"""
Main entry point for the Kalshi BTC paper trading simulator.

This script:
- Loads data
- Runs simulator for each strategy
- Prints comparison metrics
"""

from src.config import SimulationConfig
from src.simulator import Simulator
from src.strategies.no_trade import NoTradeStrategy
from src.strategies.momentum import MomentumStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.opening_auction import OpeningAuctionStrategy
from src.strategies.trend_continuation import TrendContinuationStrategy
from src.strategies.volatility_compression import VolatilityCompressionStrategy
from src.strategies.no_trade_filter import NoTradeFilterStrategy
from src.metrics import MetricsCalculator


def main():
    """Wire everything together and run simulations."""
    
    print("=" * 60)
    print("Kalshi BTC Hourly Paper Trading Simulator")
    print("=" * 60)
    
    # Create configuration
    config = SimulationConfig(
        starting_balance=10000.0,
        max_position_pct=0.1,
        fee_per_contract=0.0,
        btc_price_interval=250,
        market_duration_minutes=60,
        min_trade_price=0.01,
        max_trade_price=0.99,
        btc_prices_path="data/btc_prices_minute.csv",
        markets_path="data/kalshi_markets.csv",
        contract_prices_path="data/kalshi_contract_prices.csv"
    )
    
    print(f"\nConfiguration:")
    print(f"  Starting Balance: ${config.starting_balance:,.2f}")
    print(f"  Max Position %: {config.max_position_pct * 100}%")
    print(f"  BTC Price Interval: ${config.btc_price_interval}")
    print(f"  Fee per Contract: ${config.fee_per_contract}")
    
    # Initialize simulator
    simulator = Simulator(config)
    
    # Define strategies to test
    strategies = [
        NoTradeStrategy(),
        MomentumStrategy(lookback_minutes=3, max_position_pct=config.max_position_pct),
        MeanReversionStrategy(window_minutes=10, threshold=0.05, max_position_pct=config.max_position_pct),
        OpeningAuctionStrategy(opening_window_minutes=10, min_price_increase=0.02, max_position_pct=config.max_position_pct),
        TrendContinuationStrategy(confirmation_minutes=15, min_trend_strength=0.05, max_position_pct=config.max_position_pct),
        VolatilityCompressionStrategy(compression_window=20, compression_threshold=0.02, breakout_threshold=0.03, max_position_pct=config.max_position_pct),
        NoTradeFilterStrategy(min_btc_volatility=50.0, max_spread=0.10, lookback_minutes=30, max_position_pct=config.max_position_pct)
    ]
    
    # Run simulations
    all_results = []
    
    print(f"\nRunning simulations for {len(strategies)} strategies...")
    print("-" * 60)
    
    for strategy in strategies:
        print(f"\nSimulating: {strategy.name}")
        
        try:
            results = simulator.run(strategy)
            all_results.append(results)
            
            # Calculate and print metrics
            metrics = MetricsCalculator.calculate_metrics(results)
            MetricsCalculator.print_metrics(metrics)
            
        except Exception as e:
            print(f"Error running {strategy.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Create comparison table
    if all_results:
        print("\n" + "=" * 60)
        print("Strategy Comparison")
        print("=" * 60)
        
        comparison = MetricsCalculator.create_comparison_table(all_results)
        print(comparison.to_string(index=False))
        print()
        
        # Print strategy leaderboard
        MetricsCalculator.print_strategy_leaderboard(all_results)
        
        # Print hour-by-hour breakdown for top strategy
        if len(all_results) > 0:
            top_strategy = all_results[0]  # Already sorted by PnL
            print(f"\nShowing hourly breakdown for top strategy: {top_strategy['strategy_name']}")
            MetricsCalculator.print_hourly_breakdown(top_strategy, max_rows=20)
    
    print("\nSimulation complete!")


if __name__ == "__main__":
    main()
