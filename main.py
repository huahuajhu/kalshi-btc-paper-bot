"""
Main entry point for the Kalshi BTC paper trading simulator.

This script:
- Loads data
- Runs simulator for each strategy
- Prints comparison metrics
- Generates explainability reports
"""

from src.config import SimulationConfig
from src.simulator import Simulator
from src.strategies.no_trade import NoTradeStrategy
from src.strategies.momentum import MomentumStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
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
        MeanReversionStrategy(window_minutes=10, threshold=0.05, max_position_pct=config.max_position_pct)
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
            
            # Generate and print explainability report
            if 'explainability' in results:
                explainability = results['explainability']
                portfolio = results['portfolio']
                
                # Generate summary report
                summary_report = explainability.generate_summary_report(
                    portfolio=portfolio,
                    strategy=strategy,
                    results=results
                )
                print(summary_report)
                
                # Generate hourly reports for losing hours
                print("\n" + "=" * 70)
                print("HOURLY DIAGNOSTIC REPORTS (Losing Hours)")
                print("=" * 70)
                
                losing_hours = [h for h in results['hours_traded'] if h['hour_pnl'] < 0]
                if losing_hours:
                    for hour_result in losing_hours[:3]:  # Show first 3 losing hours
                        hourly_report = explainability.generate_hourly_report(
                            hour_result=hour_result,
                            portfolio=portfolio,
                            strategy=strategy
                        )
                        print(hourly_report)
                else:
                    print("\n✓ No losing hours to diagnose!\n")
            
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
    
    print("\nSimulation complete!")


if __name__ == "__main__":
    main()
