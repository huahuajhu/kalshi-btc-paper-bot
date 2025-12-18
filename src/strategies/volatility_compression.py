"""Volatility Compression trading strategy."""

import pandas as pd
import numpy as np
from typing import Optional
from .base import Strategy, TradeAction


class VolatilityCompressionStrategy(Strategy):
    """
    Volatility Compression strategy: Fade breakouts after stagnation.
    
    Rules:
    - Detect periods of low volatility (price compression)
    - When price breaks out after compression, fade the move (bet against it)
    - Assumption: Breakouts after stagnation often reverse
    """
    
    def __init__(self, 
                 compression_window: int = 20,
                 compression_threshold: float = 0.02,
                 breakout_threshold: float = 0.03,
                 max_position_pct: float = 0.1):
        """
        Initialize volatility compression strategy.
        
        Args:
            compression_window: Minutes to check for compression (default: 20)
            compression_threshold: Max price range to consider compressed (default: 0.02)
            breakout_threshold: Min price move to consider breakout (default: 0.03)
            max_position_pct: Maximum percentage of portfolio per trade
        """
        super().__init__(name="VolatilityCompression")
        self.compression_window = compression_window
        self.compression_threshold = compression_threshold
        self.breakout_threshold = breakout_threshold
        self.max_position_pct = max_position_pct
        self.has_traded = False
        self.was_compressed = False
        
    def reset(self):
        """Reset strategy state for a new trading hour."""
        super().reset()
        self.has_traded = False
        self.was_compressed = False
    
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
        Decide trade based on volatility compression and breakout.
        
        Returns:
            (BUY_NO, quantity) if YES breaks out after compression (fade the breakout)
            (BUY_YES, quantity) if NO breaks out after compression (fade the breakout)
            (HOLD, None) otherwise
        """
        # Don't trade if we've already traded this hour
        if self.has_traded:
            return TradeAction.HOLD, None
        
        # Need enough data to detect compression
        if len(self.history) < self.compression_window + 2:
            return TradeAction.HOLD, None
        
        # Check if prices were compressed in the lookback window
        # We need compression_window + 1 points to have a full window,
        # then exclude the last point (current) to check historical compression
        compression_window_data = self.history[-(self.compression_window + 1):-1]
        is_compressed = self._is_compressed(compression_window_data)
        
        # Track if we saw compression
        if is_compressed:
            self.was_compressed = True
        
        # Only trade if we saw compression and now see a breakout
        if not self.was_compressed:
            return TradeAction.HOLD, None
        
        # Check for breakout
        current = self.history[-1]
        previous = self.history[-2]
        
        yes_breakout = current['yes_price'] - previous['yes_price']
        no_breakout = current['no_price'] - previous['no_price']
        
        # Fade YES breakout (buy NO)
        if yes_breakout >= self.breakout_threshold:
            quantity = self._calculate_quantity(portfolio, current['no_price'])
            if quantity > 0:
                self.has_traded = True
                return TradeAction.BUY_NO, quantity
        
        # Fade NO breakout (buy YES)
        if no_breakout >= self.breakout_threshold:
            quantity = self._calculate_quantity(portfolio, current['yes_price'])
            if quantity > 0:
                self.has_traded = True
                return TradeAction.BUY_YES, quantity
        
        return TradeAction.HOLD, None
    
    def _is_compressed(self, window_data: list) -> bool:
        """
        Check if prices are compressed (low volatility).
        
        Args:
            window_data: List of price data
            
        Returns:
            True if compressed, False otherwise
        """
        if not window_data:
            return False
        
        # Calculate price ranges for both YES and NO
        yes_prices = [h['yes_price'] for h in window_data]
        no_prices = [h['no_price'] for h in window_data]
        
        yes_range = max(yes_prices) - min(yes_prices)
        no_range = max(no_prices) - min(no_prices)
        
        # Both should be compressed
        return yes_range <= self.compression_threshold and no_range <= self.compression_threshold
    
    def _calculate_quantity(self, portfolio: 'Portfolio', price: float) -> float:
        """Calculate quantity based on portfolio constraints."""
        # Calculate max quantity based on position limit
        max_value = portfolio.cash * self.max_position_pct
        max_quantity = max_value / price if price > 0 else 0
        
        # Return whole number of contracts
        return int(max_quantity)
