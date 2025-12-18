#!/usr/bin/env python3
"""
Daily Data Collection Pipeline

Orchestrates the daily collection of:
1. BTC minute-level prices from crypto exchanges
2. Kalshi hourly market data (simulated based on BTC prices)

Run this script once per day to collect and append today's data.
"""

import sys
from pathlib import Path
import subprocess
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_script(script_path: str, description: str) -> bool:
    """
    Run a Python script and return success status.
    
    Args:
        script_path: Path to the script to run
        description: Human-readable description for logging
        
    Returns:
        True if successful, False otherwise
    """
    print("\n" + "=" * 60)
    print(f"Running: {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=False,
            text=True
        )
        print(f"\n✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {description} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"\n✗ Error running {description}: {e}")
        return False


def main():
    """Main entry point for daily data collection."""
    print("=" * 60)
    print("Daily Data Collection Pipeline")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    scripts_dir = Path(__file__).parent
    
    # Step 1: Collect BTC prices
    btc_script = scripts_dir / "collect_btc_prices.py"
    btc_success = run_script(str(btc_script), "BTC Price Collection")
    
    if not btc_success:
        print("\n⚠ BTC price collection failed. Stopping pipeline.")
        sys.exit(1)
    
    # Step 2: Generate Kalshi market data
    kalshi_script = scripts_dir / "collect_kalshi_data.py"
    kalshi_success = run_script(str(kalshi_script), "Kalshi Market Data Generation")
    
    if not kalshi_success:
        print("\n⚠ Kalshi data generation failed.")
        sys.exit(1)
    
    # Summary
    print("\n" + "=" * 60)
    print("Data Collection Pipeline Complete")
    print("=" * 60)
    print("✓ BTC prices collected")
    print("✓ Kalshi markets generated")
    print("✓ All data validated and saved")
    print()
    print("Next steps:")
    print("  - Review data in the data/ directory")
    print("  - Run simulator: python main.py")
    print()


if __name__ == "__main__":
    main()
