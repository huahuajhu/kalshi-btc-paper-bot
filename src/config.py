"""Configuration for the Kalshi BTC paper trading simulator."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SimulationConfig:
    """Configuration for paper trading simulation."""
    
    # Trading parameters
    starting_balance: float = 10000.0  # Starting capital
    max_position_pct: float = 0.1  # Maximum 10% of portfolio per trade
    fee_per_contract: float = 0.0  # Fee per contract (default: $0)
    
    # Market parameters
    btc_price_interval: int = 250  # $250 intervals for market buckets
    market_duration_minutes: int = 60  # Markets last 60 minutes (1 hour)
    
    # Price constraints
    min_trade_price: float = 0.01  # Minimum contract price ($0.01)
    max_trade_price: float = 0.99  # Maximum contract price ($0.99)
    
    # Market microstructure parameters (Phase 4)
    bid_ask_spread: float = 0.02  # Bid-ask spread in price units (default: $0.02)
    slippage_per_100_contracts: float = 0.01  # Price impact per 100 contracts
    max_liquidity_per_minute: float = 500.0  # Max contracts tradeable per minute
    latency_minutes: int = 1  # Reaction delay in minutes (1-2 minutes)
    
    # Data paths
    btc_prices_path: str = "data/btc_prices_minute.csv"
    markets_path: str = "data/kalshi_markets.csv"
    contract_prices_path: str = "data/kalshi_contract_prices.csv"
    
    # Simulation parameters
    start_date: Optional[str] = None  # YYYY-MM-DD format
    end_date: Optional[str] = None    # YYYY-MM-DD format
    
    # Strategy parameters
    strategy_name: str = "no_trade"  # Default strategy
    
    def __post_init__(self):
        """Validate configuration."""
        if self.btc_price_interval <= 0:
            raise ValueError("BTC price interval must be positive")
        if self.starting_balance <= 0:
            raise ValueError("Starting balance must be positive")
        if not 0 <= self.max_position_pct <= 1:
            raise ValueError("Max position percentage must be between 0 and 1")
        if self.fee_per_contract < 0:
            raise ValueError("Fee per contract must be non-negative")
        if self.market_duration_minutes <= 0:
            raise ValueError("Market duration must be positive")
        if not 0 < self.min_trade_price < self.max_trade_price < 1:
            raise ValueError("Trade price bounds must be: 0 < min < max < 1")
        if self.bid_ask_spread < 0:
            raise ValueError("Bid-ask spread must be non-negative")
        if self.slippage_per_100_contracts < 0:
            raise ValueError("Slippage must be non-negative")
        if self.max_liquidity_per_minute <= 0:
            raise ValueError("Max liquidity per minute must be positive")
        if self.latency_minutes < 0:
            raise ValueError("Latency must be non-negative")
