"""BTC-only signal baseline strategy (ignore Kalshi prices)."""

import pandas as pd
from typing import Optional
from .base import Strategy, TradeAction


class BtcOnlyStrategy(Strategy):
    """
    BTC-only signal strategy: Trade based on BTC price movement only, 
    ignoring Kalshi contract prices.
    
    Rules:
    - If BTC price is rising, buy YES (bet price will go higher)
    - If BTC price is falling, buy NO (bet price won't go higher)
    - Otherwise hold
    
    This is a baseline strategy for counterfactual testing.
    """
    
    def __init__(self, lookback_minutes: int = 3, max_position_pct: float = 0.1):
        """
        Initialize BTC-only strategy.
        
        Args:
            lookback_minutes: Number of minutes to check for BTC trend
            max_position_pct: Maximum percentage of portfolio per trade
        """
        super().__init__(name="BtcOnly")
        self.lookback_minutes = lookback_minutes
        self.max_position_pct = max_position_pct
        self.has_traded = False  # Track if we've already traded this hour
        
    def reset(self):
        """Reset strategy state for a new trading hour."""
        super().reset()
        self.has_traded = False
    
    def on_minute(self, 
                  timestamp: pd.Timestamp,
                  btc_price: float,
                  yes_price: float,
                  no_price: float) -> None:
        """Store minute data in history."""
        self.history.append({
            'timestamp': timestamp,
            'btc_price': btc_price,
            'yes_price': yes_price,
            'no_price': no_price
        })
    
    def decide_trade(self, portfolio: 'Portfolio') -> tuple[TradeAction, Optional[float]]:
        """
        Trade based on BTC price trend, ignoring Kalshi prices.
        
        Returns:
            (BUY_YES, quantity) if BTC is rising
            (BUY_NO, quantity) if BTC is falling
            (HOLD, None) otherwise
        """
        # Don't trade if we've already traded this hour
        if self.has_traded:
            return TradeAction.HOLD, None
        
        # Need at least lookback_minutes + 1 data points
        if len(self.history) <= self.lookback_minutes:
            return TradeAction.HOLD, None
        
        # Check BTC trend
        recent = self.history[-(self.lookback_minutes + 1):]
        btc_prices = [p['btc_price'] for p in recent]
        
        # Check if consistently rising
        is_rising = all(btc_prices[i] > btc_prices[i-1] for i in range(1, len(btc_prices)))
        
        # Check if consistently falling
        is_falling = all(btc_prices[i] < btc_prices[i-1] for i in range(1, len(btc_prices)))
        
        current = self.history[-1]
        
        if is_rising:
            # BTC is rising, buy YES
            yes_price = current['yes_price']
            max_value = portfolio.cash * self.max_position_pct
            max_quantity = max_value / yes_price if yes_price > 0 else 0
            quantity = int(max_quantity)
            
            if quantity > 0:
                self.has_traded = True
                return TradeAction.BUY_YES, quantity
        
        elif is_falling:
            # BTC is falling, buy NO
            no_price = current['no_price']
            max_value = portfolio.cash * self.max_position_pct
            max_quantity = max_value / no_price if no_price > 0 else 0
            quantity = int(max_quantity)
            
            if quantity > 0:
                self.has_traded = True
                return TradeAction.BUY_NO, quantity
        
        return TradeAction.HOLD, None
