"""Mean reversion trading strategy."""

import pandas as pd
import numpy as np
from typing import Optional
from .base import Strategy, TradeAction


class MeanReversionStrategy(Strategy):
    """
    Mean reversion strategy: Trade against price extremes.
    
    Rules:
    - If YES price > rolling mean + threshold, buy NO (expect reversion)
    - If NO price > rolling mean + threshold, buy YES (expect reversion)
    - Otherwise hold
    """
    
    def __init__(self, 
                 window_minutes: int = 10,
                 threshold: float = 0.05,
                 max_position_pct: float = 0.1):
        """
        Initialize mean reversion strategy.
        
        Args:
            window_minutes: Rolling window for calculating mean (default: 10)
            threshold: Deviation threshold to trigger trade (default: 0.05)
            max_position_pct: Maximum percentage of portfolio per trade
        """
        super().__init__(name="MeanReversion")
        self.window_minutes = window_minutes
        self.threshold = threshold
        self.max_position_pct = max_position_pct
        
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
        Decide trade based on mean reversion.
        
        Returns:
            (BUY_NO, quantity) if YES is overextended
            (BUY_YES, quantity) if NO is overextended
            (HOLD, None) otherwise
        """
        # Need enough data for rolling window
        if len(self.history) < self.window_minutes:
            return TradeAction.HOLD, None
        
        # Calculate rolling means
        recent = self.history[-self.window_minutes:]
        yes_prices = [h['yes_price'] for h in recent]
        no_prices = [h['no_price'] for h in recent]
        
        yes_mean = np.mean(yes_prices)
        no_mean = np.mean(no_prices)
        
        # Current prices
        current = self.history[-1]
        current_yes = current['yes_price']
        current_no = current['no_price']
        
        # Check if YES is overextended (buy NO to bet against it)
        if current_yes > yes_mean + self.threshold:
            quantity = self._calculate_quantity(portfolio, current_no)
            if quantity > 0:
                return TradeAction.BUY_NO, quantity
        
        # Check if NO is overextended (buy YES to bet against it)
        if current_no > no_mean + self.threshold:
            quantity = self._calculate_quantity(portfolio, current_yes)
            if quantity > 0:
                return TradeAction.BUY_YES, quantity
        
        return TradeAction.HOLD, None
    
    def _calculate_quantity(self, portfolio: 'Portfolio', price: float) -> float:
        """Calculate quantity based on portfolio constraints."""
        # Calculate max quantity based on position limit
        max_value = portfolio.cash * self.max_position_pct
        max_quantity = max_value / price if price > 0 else 0
        
        # Return whole number of contracts
        return int(max_quantity)
