"""
Generate ML-ready dataset from simulator.

This script demonstrates how to use the simulator to create a dataset
suitable for machine learning tasks.
"""

from src.config import SimulationConfig
from src.simulator import Simulator
from src.strategies.no_trade import NoTradeStrategy


def main():
    """Generate ML-ready dataset from simulation."""
    
    print("=" * 60)
    print("ML-Ready Dataset Generator")
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
    print(f"  Data Path: {config.btc_prices_path}")
    print(f"  Markets Path: {config.markets_path}")
    print(f"  Contract Prices Path: {config.contract_prices_path}")
    
    # Initialize simulator
    simulator = Simulator(config)
    
    # Use NoTradeStrategy since we only care about collecting data
    strategy = NoTradeStrategy()
    
    print(f"\nRunning simulation with dataset collection enabled...")
    print(f"Strategy: {strategy.name} (data collection only)")
    
    try:
        # Run simulation with dataset collection enabled
        results = simulator.run(strategy, collect_dataset=True)
        
        print(f"\nSimulation complete!")
        print(f"  Hours traded: {len(results['hours_traded'])}")
        
        # Get the dataset
        dataset = simulator.get_dataset()
        
        if dataset is not None and not dataset.empty:
            print(f"\nDataset summary:")
            print(f"  Total rows: {len(dataset)}")
            print(f"  Features: {', '.join(dataset.columns)}")
            print(f"\nFirst few rows:")
            print(dataset.head(10).to_string())
            
            # Save dataset
            output_path = "data/ml_dataset.csv"
            simulator.save_dataset(output_path)
            print(f"\n✓ Dataset saved successfully!")
            
            # Print statistics
            print(f"\nDataset statistics:")
            print(f"  Label distribution:")
            print(f"    YES wins (label=1): {(dataset['label'] == 1).sum()}")
            print(f"    NO wins (label=0): {(dataset['label'] == 0).sum()}")
            print(f"\n  Feature ranges:")
            for col in ['btc_return_5m', 'btc_return_15m', 'spread', 'volatility']:
                if col in dataset.columns:
                    print(f"    {col}: [{dataset[col].min():.6f}, {dataset[col].max():.6f}]")
        else:
            print("\nWarning: No dataset was collected!")
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
