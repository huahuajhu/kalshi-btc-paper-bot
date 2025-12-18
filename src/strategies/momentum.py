"""Momentum-based trading strategy."""

import pandas as pd
from typing import Optional
from .base import Strategy, TradeAction


class MomentumStrategy(Strategy):
    """
    Momentum strategy: Buy based on consecutive price increases.
    
    Rules:
    - If YES price increased for N consecutive minutes, buy YES
    - If NO price increased for N consecutive minutes, buy NO
    - Otherwise hold
    """
    
    def __init__(self, lookback_minutes: int = 3, max_position_pct: float = 0.1):
        """
        Initialize momentum strategy.
        
        Args:
            lookback_minutes: Number of consecutive minutes to check (default: 3)
            max_position_pct: Maximum percentage of portfolio per trade
        """
        super().__init__(name="Momentum")
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
        Decide trade based on momentum.
        
        Returns:
            (BUY_YES, quantity) if YES momentum detected
            (BUY_NO, quantity) if NO momentum detected
            (HOLD, None) otherwise
        """
        # Don't trade if we've already traded this hour
        if self.has_traded:
            return TradeAction.HOLD, None
        
        # Need at least lookback_minutes + 1 data points
        if len(self.history) <= self.lookback_minutes:
            return TradeAction.HOLD, None
        
        # Check for YES momentum
        yes_momentum = self._check_yes_momentum()
        if yes_momentum:
            quantity = self._calculate_quantity(portfolio, is_yes=True)
            if quantity > 0:
                self.has_traded = True  # Mark that we've traded
                return TradeAction.BUY_YES, quantity
        
        # Check for NO momentum
        no_momentum = self._check_no_momentum()
        if no_momentum:
            quantity = self._calculate_quantity(portfolio, is_yes=False)
            if quantity > 0:
                self.has_traded = True  # Mark that we've traded
                return TradeAction.BUY_NO, quantity
        
        return TradeAction.HOLD, None
    
    def _check_yes_momentum(self) -> bool:
        """Check if YES price increased for N consecutive minutes."""
        recent = self.history[-(self.lookback_minutes + 1):]
        
        for i in range(1, len(recent)):
            if recent[i]['yes_price'] <= recent[i-1]['yes_price']:
                return False
        
        return True
    
    def _check_no_momentum(self) -> bool:
        """Check if NO price increased for N consecutive minutes."""
        recent = self.history[-(self.lookback_minutes + 1):]
        
        for i in range(1, len(recent)):
            if recent[i]['no_price'] <= recent[i-1]['no_price']:
                return False
        
        return True
    
    def _calculate_quantity(self, portfolio: 'Portfolio', is_yes: bool) -> float:
        """Calculate quantity based on portfolio constraints."""
        current = self.history[-1]
        price = current['yes_price'] if is_yes else current['no_price']
        
        # Calculate max quantity based on position limit
        max_value = portfolio.cash * self.max_position_pct
        max_quantity = max_value / price if price > 0 else 0
        
        # Return whole number of contracts
        return int(max_quantity)
