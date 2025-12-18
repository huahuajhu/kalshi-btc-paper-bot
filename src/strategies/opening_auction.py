"""Opening Auction trading strategy."""

import pandas as pd
from typing import Optional
from .base import Strategy, TradeAction


class OpeningAuctionStrategy(Strategy):
    """
    Opening Auction strategy: Trade during the first 5-10 minutes of the hour.
    
    Rules:
    - Only trade within the opening window (first 5-10 minutes)
    - If YES price is rising in the opening, buy YES
    - If NO price is rising in the opening, buy NO
    - After the opening window, hold positions until resolution
    """
    
    def __init__(self, 
                 opening_window_minutes: int = 10,
                 min_price_increase: float = 0.02,
                 max_position_pct: float = 0.1):
        """
        Initialize opening auction strategy.
        
        Args:
            opening_window_minutes: Number of minutes from hour start to trade (default: 10)
            min_price_increase: Minimum price increase to trigger trade (default: 0.02)
            max_position_pct: Maximum percentage of portfolio per trade
        """
        super().__init__(name="OpeningAuction")
        self.opening_window_minutes = opening_window_minutes
        self.min_price_increase = min_price_increase
        self.max_position_pct = max_position_pct
        self.has_traded = False
        self.hour_start_time = None
        
    def reset(self):
        """Reset strategy state for a new trading hour."""
        super().reset()
        self.has_traded = False
        self.hour_start_time = None
    
    def on_minute(self, 
                  timestamp: pd.Timestamp,
                  btc_price: float,
                  yes_price: float,
                  no_price: float) -> None:
        """Store minute data in history."""
        # Record the hour start time from the first minute
        if self.hour_start_time is None:
            self.hour_start_time = timestamp
            
        self.history.append({
            'timestamp': timestamp,
            'btc_price': btc_price,
            'yes_price': yes_price,
            'no_price': no_price
        })
    
    def decide_trade(self, portfolio: 'Portfolio') -> tuple[TradeAction, Optional[float]]:
        """
        Decide trade based on opening auction dynamics.
        
        Returns:
            (BUY_YES, quantity) if YES momentum in opening window
            (BUY_NO, quantity) if NO momentum in opening window
            (HOLD, None) otherwise
        """
        # Don't trade if we've already traded this hour
        if self.has_traded:
            return TradeAction.HOLD, None
        
        # Need at least 2 data points to check momentum
        if len(self.history) < 2:
            return TradeAction.HOLD, None
        
        current = self.history[-1]
        
        # Check if we're still in the opening window
        if self.hour_start_time is None:
            return TradeAction.HOLD, None
            
        minutes_elapsed = (current['timestamp'] - self.hour_start_time).total_seconds() / 60.0
        
        # Only trade during opening window
        if minutes_elapsed > self.opening_window_minutes:
            return TradeAction.HOLD, None
        
        # Calculate price change from start to current
        start_yes = self.history[0]['yes_price']
        start_no = self.history[0]['no_price']
        current_yes = current['yes_price']
        current_no = current['no_price']
        
        yes_change = current_yes - start_yes
        no_change = current_no - start_no
        
        # Handle edge case: if both sides have equal momentum above threshold, do not trade
        if (yes_change >= self.min_price_increase and 
            no_change >= self.min_price_increase and 
            yes_change == no_change):
            return TradeAction.HOLD, None
        
        # Trade based on significant price momentum on only one side
        if (yes_change >= self.min_price_increase and 
            yes_change > no_change and 
            no_change < self.min_price_increase):
            quantity = self._calculate_quantity(portfolio, current_yes, self.max_position_pct)
            if quantity > 0:
                self.has_traded = True
                return TradeAction.BUY_YES, quantity
        
        if (no_change >= self.min_price_increase and 
            no_change > yes_change and 
            yes_change < self.min_price_increase):
            quantity = self._calculate_quantity(portfolio, current_no, self.max_position_pct)
            if quantity > 0:
                self.has_traded = True
                return TradeAction.BUY_NO, quantity
        
        return TradeAction.HOLD, None
