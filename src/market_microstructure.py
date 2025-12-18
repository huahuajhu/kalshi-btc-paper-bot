"""Market microstructure modeling for realistic trading conditions."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np


@dataclass
class TradeExecution:
    """Result of trade execution with microstructure effects."""
    executed: bool
    execution_price: float
    quantity_executed: float
    slippage: float
    spread_cost: float
    reason: str = ""  # Reason if not executed


class MarketMicrostructure:
    """
    Models realistic market microstructure effects:
    - Bid/ask spreads
    - Slippage from market impact
    - Limited liquidity per minute
    - Latency delays
    """
    
    def __init__(self,
                 bid_ask_spread: float = 0.02,
                 slippage_per_100_contracts: float = 0.01,
                 max_liquidity_per_minute: float = 500.0,
                 latency_minutes: int = 1):
        """
        Initialize market microstructure model.
        
        Args:
            bid_ask_spread: Bid-ask spread in price units (e.g., 0.02 = 2 cents)
            slippage_per_100_contracts: Price impact per 100 contracts traded
            max_liquidity_per_minute: Maximum contracts that can be traded per minute
            latency_minutes: Delay between decision and execution (1-2 minutes)
        """
        self.bid_ask_spread = bid_ask_spread
        self.slippage_per_100_contracts = slippage_per_100_contracts
        self.max_liquidity_per_minute = max_liquidity_per_minute
        self.latency_minutes = latency_minutes
        
        # Track liquidity consumption per timestamp
        self.liquidity_consumed: Dict[pd.Timestamp, float] = {}
        
        # Track pending orders (for latency simulation)
        self.pending_orders = []
    
    def reset_hour(self):
        """Reset state for a new trading hour."""
        self.liquidity_consumed.clear()
        self.pending_orders.clear()
    
    def get_execution_price(self,
                           mid_price: float,
                           quantity: float,
                           side: str) -> Tuple[float, float, float]:
        """
        Calculate execution price including spread and slippage.
        
        Args:
            mid_price: Mid-market price
            quantity: Number of contracts to trade
            side: "buy" or "sell"
            
        Returns:
            Tuple of (execution_price, spread_cost, slippage)
        """
        # Apply bid-ask spread (buyers pay ask, sellers receive bid)
        half_spread = self.bid_ask_spread / 2
        
        if side == "buy":
            # Buying: pay the ask price (mid + half spread)
            price_with_spread = mid_price + half_spread
        else:
            # Selling: receive the bid price (mid - half spread)
            price_with_spread = mid_price - half_spread
        
        # Calculate slippage based on order size
        # Larger orders move the price more
        slippage_factor = (quantity / 100.0) * self.slippage_per_100_contracts
        
        if side == "buy":
            # Price moves up when buying
            slippage = slippage_factor
            execution_price = price_with_spread + slippage
        else:
            # Price moves down when selling
            slippage = slippage_factor
            execution_price = price_with_spread - slippage
        
        # Clamp to valid price range [0.01, 0.99]
        execution_price = np.clip(execution_price, 0.01, 0.99)
        
        spread_cost = half_spread
        
        return execution_price, spread_cost, slippage
    
    def check_liquidity(self, 
                       timestamp: pd.Timestamp,
                       quantity: float) -> Tuple[bool, float]:
        """
        Check if sufficient liquidity is available at this timestamp.
        
        Args:
            timestamp: Current timestamp
            quantity: Desired trade quantity
            
        Returns:
            Tuple of (can_execute, available_quantity)
        """
        # Get how much liquidity has been consumed this minute
        consumed = self.liquidity_consumed.get(timestamp, 0.0)
        available = self.max_liquidity_per_minute - consumed
        
        if available <= 0:
            return False, 0.0
        
        if quantity <= available:
            return True, quantity
        else:
            # Partial fill possible
            return True, available
    
    def consume_liquidity(self, timestamp: pd.Timestamp, quantity: float):
        """
        Record liquidity consumption at a timestamp.
        
        Args:
            timestamp: Timestamp of the trade
            quantity: Quantity traded
        """
        current = self.liquidity_consumed.get(timestamp, 0.0)
        self.liquidity_consumed[timestamp] = current + quantity
    
    def add_pending_order(self,
                         decision_time: pd.Timestamp,
                         action: str,
                         quantity: float,
                         target_price: float):
        """
        Add a pending order that will execute after latency delay.
        
        Args:
            decision_time: When the decision was made
            action: "BUY_YES" or "BUY_NO"
            quantity: Number of contracts
            target_price: Price at decision time
        """
        self.pending_orders.append({
            'decision_time': decision_time,
            'action': action,
            'quantity': quantity,
            'target_price': target_price
        })
    
    def get_executable_orders(self, current_time: pd.Timestamp) -> list:
        """
        Get orders that are ready to execute (past latency delay).
        
        Args:
            current_time: Current timestamp
            
        Returns:
            List of orders ready to execute
        """
        executable = []
        remaining = []
        
        for order in self.pending_orders:
            # Calculate time difference in minutes
            time_diff = (current_time - order['decision_time']).total_seconds() / 60
            
            if time_diff >= self.latency_minutes:
                executable.append(order)
            else:
                remaining.append(order)
        
        # Update pending orders list
        self.pending_orders = remaining
        
        return executable
    
    def execute_trade(self,
                     timestamp: pd.Timestamp,
                     mid_price: float,
                     quantity: float,
                     side: str = "buy") -> TradeExecution:
        """
        Execute a trade with all microstructure effects applied.
        
        Args:
            timestamp: Trade timestamp
            mid_price: Mid-market price
            quantity: Desired quantity
            side: "buy" or "sell"
            
        Returns:
            TradeExecution object with results
        """
        # Check liquidity constraints
        can_execute, available_qty = self.check_liquidity(timestamp, quantity)
        
        if not can_execute:
            return TradeExecution(
                executed=False,
                execution_price=0.0,
                quantity_executed=0.0,
                slippage=0.0,
                spread_cost=0.0,
                reason="Insufficient liquidity"
            )
        
        # Use available quantity (might be partial fill)
        final_quantity = min(quantity, available_qty)
        
        # Calculate execution price with spread and slippage
        exec_price, spread_cost, slippage = self.get_execution_price(
            mid_price, final_quantity, side
        )
        
        # Consume liquidity
        self.consume_liquidity(timestamp, final_quantity)
        
        return TradeExecution(
            executed=True,
            execution_price=exec_price,
            quantity_executed=final_quantity,
            slippage=slippage,
            spread_cost=spread_cost,
            reason="Executed successfully"
        )
