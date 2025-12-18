"""Trend Continuation trading strategy."""

import pandas as pd
import numpy as np
from typing import Optional
from .base import Strategy, TradeAction


class TrendContinuationStrategy(Strategy):
    """
    Trend Continuation strategy: Trade after momentum confirmation.
    
    Rules:
    - Wait for a clear trend to establish (price moving in one direction)
    - Confirm momentum with volume (price change magnitude)
    - Enter in the direction of the confirmed trend
    - Only take one position per hour
    """
    
    def __init__(self, 
                 confirmation_minutes: int = 15,
                 min_trend_strength: float = 0.05,
                 max_position_pct: float = 0.1):
        """
        Initialize trend continuation strategy.
        
        Args:
            confirmation_minutes: Minutes to observe before confirming trend (default: 15)
            min_trend_strength: Minimum price change to confirm trend (default: 0.05)
            max_position_pct: Maximum percentage of portfolio per trade
        """
        super().__init__(name="TrendContinuation")
        self.confirmation_minutes = confirmation_minutes
        self.min_trend_strength = min_trend_strength
        self.max_position_pct = max_position_pct
        self.has_traded = False
        
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
        Decide trade based on trend continuation.
        
        Returns:
            (BUY_YES, quantity) if YES trend confirmed
            (BUY_NO, quantity) if NO trend confirmed
            (HOLD, None) otherwise
        """
        # Don't trade if we've already traded this hour
        if self.has_traded:
            return TradeAction.HOLD, None
        
        # Need enough data to confirm trend
        if len(self.history) < self.confirmation_minutes:
            return TradeAction.HOLD, None
        
        # Analyze trend over confirmation period
        lookback = self.history[-self.confirmation_minutes:]
        
        # Calculate trend metrics
        yes_trend = self._calculate_trend([h['yes_price'] for h in lookback])
        no_trend = self._calculate_trend([h['no_price'] for h in lookback])
        
        current = self.history[-1]
        
        # Trade in direction of strongest trend
        if yes_trend >= self.min_trend_strength and yes_trend > no_trend:
            quantity = self._calculate_quantity(portfolio, current['yes_price'])
            if quantity > 0:
                self.has_traded = True
                return TradeAction.BUY_YES, quantity
        
        if no_trend >= self.min_trend_strength and no_trend > yes_trend:
            quantity = self._calculate_quantity(portfolio, current['no_price'])
            if quantity > 0:
                self.has_traded = True
                return TradeAction.BUY_NO, quantity
        
        return TradeAction.HOLD, None
    
    def _calculate_trend(self, prices: list) -> float:
        """
        Calculate trend strength as normalized price change.
        
        Args:
            prices: List of prices over time
            
        Returns:
            Trend strength (positive = upward trend)
        """
        if len(prices) < 2:
            return 0.0
        
        # Calculate simple slope (price change over time period)
        slope = (prices[-1] - prices[0]) / len(prices)
        
        # Normalize by average price to get percentage trend
        avg_price = np.mean(prices)
        if avg_price > 0:
            normalized_slope = slope / avg_price * len(prices)
        else:
            normalized_slope = 0.0
        
        return normalized_slope
    
    def _calculate_quantity(self, portfolio: 'Portfolio', price: float) -> float:
        """Calculate quantity based on portfolio constraints."""
        # Calculate max quantity based on position limit
        max_value = portfolio.cash * self.max_position_pct
        max_quantity = max_value / price if price > 0 else 0
        
        # Return whole number of contracts
        return int(max_quantity)
