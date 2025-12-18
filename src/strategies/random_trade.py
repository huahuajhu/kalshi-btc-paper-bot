"""Random trading baseline strategy."""

import pandas as pd
import random
from typing import Optional
from .base import Strategy, TradeAction


class RandomStrategy(Strategy):
    """
    Random trading strategy: Randomly buys YES, NO, or holds.
    
    This is a baseline strategy for counterfactual testing.
    """
    
    def __init__(self, max_position_pct: float = 0.1, seed: int = 42):
        """
        Initialize random strategy.
        
        Args:
            max_position_pct: Maximum percentage of portfolio per trade
            seed: Random seed for reproducibility
        """
        super().__init__(name="Random")
        self.max_position_pct = max_position_pct
        self.seed = seed
        self.rng = random.Random(seed)  # Use instance-level random generator
        self.has_traded = False  # Track if we've already traded this hour
        
    def reset(self):
        """Reset strategy state for a new trading hour."""
        super().reset()
        self.has_traded = False
        # Reset random state for reproducibility across runs
        self.rng = random.Random(self.seed)
    
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
        Randomly decide to buy YES, NO, or hold on the first minute of each hour.
        
        Returns:
            Random action (BUY_YES, BUY_NO, or HOLD) with quantity
        """
        # Don't trade if we've already traded this hour
        if self.has_traded:
            return TradeAction.HOLD, None
        
        # Need at least one data point
        if len(self.history) == 0:
            return TradeAction.HOLD, None
        
        # Randomly choose action on first minute
        current = self.history[-1]
        action_choice = self.rng.choice([TradeAction.BUY_YES, TradeAction.BUY_NO, TradeAction.HOLD])
        
        if action_choice == TradeAction.HOLD:
            self.has_traded = True  # For HOLD, mark as traded to avoid retry
            return TradeAction.HOLD, None
        
        # Calculate quantity
        if action_choice == TradeAction.BUY_YES:
            price = current['yes_price']
        else:  # BUY_NO
            price = current['no_price']
        
        max_value = portfolio.cash * self.max_position_pct
        max_quantity = max_value / price if price > 0 else 0
        quantity = int(max_quantity)
        
        if quantity > 0:
            self.has_traded = True  # Only mark as traded if we actually trade
            return action_choice, quantity
        
        # Don't set has_traded if quantity is 0 - allow retry if cash becomes available
        return TradeAction.HOLD, None
