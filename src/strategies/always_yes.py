"""Always buy YES baseline strategy."""

import pandas as pd
from typing import Optional
from .base import Strategy, TradeAction


class AlwaysYesStrategy(Strategy):
    """
    Always buy YES strategy: Buys YES contracts on every opportunity.
    
    This is a baseline strategy for counterfactual testing.
    """
    
    def __init__(self, max_position_pct: float = 0.1):
        """
        Initialize always YES strategy.
        
        Args:
            max_position_pct: Maximum percentage of portfolio per trade
        """
        super().__init__(name="AlwaysYes")
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
        Always buy YES on the first minute of each hour.
        
        Returns:
            (BUY_YES, quantity) on first minute
            (HOLD, None) after first trade
        """
        # Don't trade if we've already traded this hour
        if self.has_traded:
            return TradeAction.HOLD, None
        
        # Need at least one data point
        if len(self.history) == 0:
            return TradeAction.HOLD, None
        
        # Buy YES on first minute
        current = self.history[-1]
        yes_price = current['yes_price']
        
        # Calculate quantity based on portfolio constraints
        max_value = portfolio.cash * self.max_position_pct
        max_quantity = max_value / yes_price if yes_price > 0 else 0
        quantity = int(max_quantity)
        
        if quantity > 0:
            self.has_traded = True  # Only mark as traded if we actually trade
            return TradeAction.BUY_YES, quantity
        
        # Don't set has_traded if quantity is 0 - allow retry if cash becomes available
        return TradeAction.HOLD, None
