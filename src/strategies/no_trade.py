"""No-trade baseline strategy."""

import pandas as pd
from typing import Optional
from .base import Strategy, TradeAction


class NoTradeStrategy(Strategy):
    """
    No-trade strategy: Never trades, always holds.
    
    Serves as a baseline for comparison.
    """
    
    def __init__(self):
        """Initialize no-trade strategy."""
        super().__init__(name="NoTrade")
        
    def on_minute(self, 
                  timestamp: pd.Timestamp,
                  btc_price: float,
                  yes_price: float,
                  no_price: float) -> None:
        """Store minute data in history (for potential analysis)."""
        self.history.append({
            'timestamp': timestamp,
            'btc_price': btc_price,
            'yes_price': yes_price,
            'no_price': no_price
        })
    
    def decide_trade(self, portfolio: 'Portfolio') -> tuple[TradeAction, Optional[float]]:
        """
        Always hold - never trade.
        
        Returns:
            (HOLD, None) always
        """
        return TradeAction.HOLD, None
