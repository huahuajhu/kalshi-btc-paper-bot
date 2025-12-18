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
