"""Base strategy class for trading decisions."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
import pandas as pd


class TradeAction(Enum):
    """Possible trade actions."""
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    HOLD = "HOLD"


class Strategy(ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, name: str):
        """
        Initialize strategy.
        
        Args:
            name: Name of the strategy
        """
        self.name = name
        self.history = []  # Store minute-by-minute data
        
    def reset(self):
        """Reset strategy state for a new trading hour."""
        self.history = []
    
    @abstractmethod
    def on_minute(self, 
                  timestamp: pd.Timestamp,
                  btc_price: float,
                  yes_price: float,
                  no_price: float) -> None:
        """
        Process minute-level market data.
        
        Args:
            timestamp: Current timestamp
            btc_price: Current BTC price
            yes_price: Current YES contract price
            no_price: Current NO contract price
        """
        pass
    
    @abstractmethod
    def decide_trade(self, portfolio: 'Portfolio') -> tuple[TradeAction, Optional[float]]:
        """
        Decide on trade action based on current state.
        
        Args:
            portfolio: Current portfolio state
            
        Returns:
            Tuple of (action, quantity) where:
            - action: BUY_YES, BUY_NO, or HOLD
            - quantity: Number of contracts to buy (None if HOLD)
        """
        pass
    
    def get_current_prices(self) -> Optional[dict]:
        """Get the most recent price data."""
        if not self.history:
            return None
        return self.history[-1]
    
    def _calculate_quantity(self, portfolio: 'Portfolio', price: float, max_position_pct: float) -> float:
        """
        Calculate quantity based on portfolio constraints.
        
        Args:
            portfolio: Current portfolio state
            price: Price per contract
            max_position_pct: Maximum percentage of portfolio per trade
            
        Returns:
            Whole number of contracts to buy
        """
        # Calculate max quantity based on position limit
        max_value = portfolio.cash * max_position_pct
        max_quantity = max_value / price if price > 0 else 0
        
        # Return whole number of contracts
        return int(max_quantity)
