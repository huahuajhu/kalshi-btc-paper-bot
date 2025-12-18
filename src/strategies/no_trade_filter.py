"""No-Trade Filter strategy."""

import pandas as pd
from typing import Optional
from .base import Strategy, TradeAction


class NoTradeFilterStrategy(Strategy):
    """
    No-Trade Filter strategy: Skip low BTC movement or wide spreads.
    
    This strategy wraps another strategy and adds filters to avoid trading
    in unfavorable conditions:
    - Skip hours with low BTC volatility (not enough movement to profit)
    - Skip when YES/NO spreads are too wide (poor liquidity)
    
    For standalone use, it implements a simple momentum strategy but only
    trades when conditions pass the filters.
    """
    
    def __init__(self, 
                 min_btc_volatility: float = 50.0,
                 max_spread: float = 0.10,
                 lookback_minutes: int = 30,
                 max_position_pct: float = 0.1):
        """
        Initialize no-trade filter strategy.
        
        Args:
            min_btc_volatility: Minimum BTC price range to consider trading (default: $50)
            max_spread: Maximum acceptable YES+NO spread (default: 0.10)
            lookback_minutes: Minutes to check for volatility (default: 30)
            max_position_pct: Maximum percentage of portfolio per trade
        """
        super().__init__(name="NoTradeFilter")
        self.min_btc_volatility = min_btc_volatility
        self.max_spread = max_spread
        self.lookback_minutes = lookback_minutes
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
        Decide trade based on filters and simple momentum.
        
        Returns:
            Trade action only if filters pass, otherwise HOLD
        """
        # Don't trade if we've already traded this hour
        if self.has_traded:
            return TradeAction.HOLD, None
        
        # Need enough data
        if len(self.history) < self.lookback_minutes:
            return TradeAction.HOLD, None
        
        # Apply filters
        if not self._passes_filters():
            return TradeAction.HOLD, None
        
        # If filters pass, use simple momentum strategy
        lookback = self.history[-5:]  # Last 5 minutes
        
        yes_prices = [h['yes_price'] for h in lookback]
        no_prices = [h['no_price'] for h in lookback]
        
        # Calculate total price change to detect momentum (less restrictive than all increasing)
        yes_total_change = yes_prices[-1] - yes_prices[0]
        no_total_change = no_prices[-1] - no_prices[0]
        
        # Require at least 1% change to consider momentum
        min_momentum_threshold = 0.01
        
        current = self.history[-1]
        
        if yes_total_change >= min_momentum_threshold and yes_total_change > no_total_change:
            quantity = self._calculate_quantity(portfolio, current['yes_price'], self.max_position_pct)
            if quantity > 0:
                self.has_traded = True
                return TradeAction.BUY_YES, quantity
        
        if no_total_change >= min_momentum_threshold and no_total_change > yes_total_change:
            quantity = self._calculate_quantity(portfolio, current['no_price'], self.max_position_pct)
            if quantity > 0:
                self.has_traded = True
                return TradeAction.BUY_NO, quantity
        
        return TradeAction.HOLD, None
    
    def _passes_filters(self) -> bool:
        """
        Check if current conditions pass trading filters.
        
        Returns:
            True if filters pass, False otherwise
        """
        lookback = self.history[-self.lookback_minutes:]
        
        # Filter 1: Check BTC volatility
        btc_prices = [h['btc_price'] for h in lookback]
        btc_range = max(btc_prices) - min(btc_prices)
        
        if btc_range < self.min_btc_volatility:
            return False  # Not enough BTC movement
        
        # Filter 2: Check spread (YES + NO should be close to 1.0)
        current = self.history[-1]
        spread = abs((current['yes_price'] + current['no_price']) - 1.0)
        
        if spread > self.max_spread:
            return False  # Spread too wide, poor liquidity
        
        return True
