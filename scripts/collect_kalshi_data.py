"""
Collect Kalshi BTC hourly market data.

Since Kalshi doesn't have a public API for historical data and this is for 
paper trading, this script simulates/generates Kalshi market data based on 
actual BTC prices.

Generates:
1. Hourly markets with strike prices at $250 intervals
2. YES/NO contract prices that evolve minute-by-minute based on BTC price movements
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import sys

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_btc_prices(filepath: str) -> pd.DataFrame:
    """
    Load BTC prices from CSV.
    
    Args:
        filepath: Path to BTC prices CSV
        
    Returns:
        DataFrame with timestamp and price columns
    """
    if not Path(filepath).exists():
        raise FileNotFoundError(f"BTC prices file not found: {filepath}")
    
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def get_todays_btc_prices(btc_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter BTC prices for today only.
    
    Args:
        btc_df: DataFrame with all BTC prices
        
    Returns:
        DataFrame with today's prices only
    """
    today = datetime.now(timezone.utc).date()
    btc_df = btc_df.copy()
    btc_df['date'] = pd.to_datetime(btc_df['timestamp']).dt.date
    today_df = btc_df[btc_df['date'] == today].copy()
    today_df = today_df.drop('date', axis=1)
    return today_df


def generate_strike_prices(btc_price: float, interval: int = 250, num_strikes: int = 5) -> list:
    """
    Generate strike prices around current BTC price.
    
    Args:
        btc_price: Current BTC price
        interval: Strike interval in dollars (default: $250)
        num_strikes: Number of strikes above and below (default: 5)
        
    Returns:
        List of strike prices
    """
    # Round to nearest interval
    base_strike = round(btc_price / interval) * interval
    
    # Generate strikes above and below
    strikes = []
    for i in range(-num_strikes, num_strikes + 1):
        strikes.append(base_strike + (i * interval))
    
    return sorted(strikes)


def calculate_contract_prices(btc_price: float, strike_price: float, 
                              time_remaining_minutes: int, 
                              volatility: float = 0.02) -> tuple:
    """
    Calculate YES/NO prices based on implied probability.
    
    Simple model:
    - If BTC is far above strike: YES price high, NO price low
    - If BTC is far below strike: YES price low, NO price high
    - As time runs out, prices converge to 0.99/0.01 or 0.01/0.99
    
    Args:
        btc_price: Current BTC price
        strike_price: Strike price for the market
        time_remaining_minutes: Minutes until market close
        volatility: Price volatility factor (default: 0.02)
        
    Returns:
        Tuple of (yes_price, no_price)
    """
    # Calculate distance from strike as percentage
    distance_pct = (btc_price - strike_price) / strike_price
    
    # Time decay factor (less uncertainty as time runs out)
    time_factor = time_remaining_minutes / 60.0  # 0 to 1
    
    # Base probability using sigmoid-like function
    # Positive distance -> higher YES probability
    base_prob = 1 / (1 + np.exp(-distance_pct * 50))
    
    # Add some randomness/volatility
    noise = np.random.normal(0, volatility * time_factor)
    yes_price = base_prob + noise
    
    # Ensure prices are within bounds [0.01, 0.99]
    yes_price = np.clip(yes_price, 0.01, 0.99)
    no_price = 1.00 - yes_price
    
    # Round to 2 decimal places
    yes_price = round(yes_price, 2)
    no_price = round(1.00 - yes_price, 2)  # Ensure sum is exactly 1.00
    
    return yes_price, no_price


def generate_hourly_markets(btc_df: pd.DataFrame, interval: int = 250) -> pd.DataFrame:
    """
    Generate hourly markets from BTC price data.
    
    Args:
        btc_df: DataFrame with minute-level BTC prices
        interval: Strike price interval
        
    Returns:
        DataFrame with hourly markets
    """
    markets = []
    
    # Group by hour (use 'h' instead of 'H')
    btc_df = btc_df.copy()
    btc_df['hour_start'] = btc_df['timestamp'].dt.floor('h')
    
    for hour_start, hour_data in btc_df.groupby('hour_start'):
        # Get BTC price at hour start
        first_price = hour_data.iloc[0]['price']
        
        # Generate strike prices
        strikes = generate_strike_prices(first_price, interval)
        
        # Create market entries
        for strike in strikes:
            markets.append({
                'hour_start': hour_start,
                'strike_price': int(strike)
            })
    
    return pd.DataFrame(markets)


def generate_contract_prices(btc_df: pd.DataFrame, markets_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate minute-by-minute YES/NO prices for each market.
    
    Args:
        btc_df: DataFrame with minute-level BTC prices
        markets_df: DataFrame with hourly markets
        
    Returns:
        DataFrame with contract prices
    """
    contract_prices = []
    
    # Ensure markets_df hour_start is datetime
    if 'hour_start' in markets_df.columns:
        markets_df = markets_df.copy()
        markets_df['hour_start'] = pd.to_datetime(markets_df['hour_start'])
    
    # Add hour_start to BTC data  
    btc_df = btc_df.copy()
    btc_df['hour_start'] = btc_df['timestamp'].dt.floor('h')  # Use 'h' instead of 'H'
    
    # For each market (hour + strike combination)
    for _, market in markets_df.iterrows():
        hour_start = pd.to_datetime(market['hour_start'])
        strike_price = market['strike_price']
        
        # Get BTC prices for this hour
        hour_data = btc_df[btc_df['hour_start'] == hour_start].copy()
        
        if hour_data.empty:
            continue
        
        # Generate prices for each minute
        for idx, row in hour_data.iterrows():
            timestamp = row['timestamp']
            btc_price = row['price']
            
            # Calculate time remaining
            minutes_elapsed = (timestamp - hour_start).total_seconds() / 60
            time_remaining = max(0, 60 - minutes_elapsed)
            
            # Calculate YES/NO prices
            yes_price, no_price = calculate_contract_prices(
                btc_price, strike_price, time_remaining
            )
            
            contract_prices.append({
                'timestamp': timestamp,
                'strike_price': strike_price,
                'yes_price': yes_price,
                'no_price': no_price
            })
    
    return pd.DataFrame(contract_prices)


def append_to_csv(new_data: pd.DataFrame, filepath: str, key_columns: list):
    """
    Append new data to existing CSV file, avoiding duplicates.
    
    Args:
        new_data: DataFrame with new data
        filepath: Path to CSV file
        key_columns: Columns to use for duplicate detection
    """
    filepath = Path(filepath)
    
    if new_data.empty:
        print("No new data to append")
        return
    
    # Ensure data directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert timestamp columns to string format if present
    if 'timestamp' in new_data.columns:
        new_data['timestamp'] = new_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    if 'hour_start' in new_data.columns:
        new_data['hour_start'] = new_data['hour_start'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Load existing data if file exists
    if filepath.exists():
        print(f"Loading existing data from {filepath}...")
        existing_data = pd.read_csv(filepath)
        
        # Combine and remove duplicates
        combined = pd.concat([existing_data, new_data], ignore_index=True)
        combined = combined.drop_duplicates(subset=key_columns, keep='last')
        combined = combined.sort_values(key_columns)
        
        # Save back
        combined.to_csv(filepath, index=False)
        
        new_count = len(combined) - len(existing_data)
        print(f"Added {new_count} new records (removed {len(new_data) - new_count} duplicates)")
        print(f"Total records: {len(combined)}")
    else:
        # Create new file
        print(f"Creating new file: {filepath}")
        new_data.to_csv(filepath, index=False)
        print(f"Saved {len(new_data)} records")


def validate_contract_prices(df: pd.DataFrame) -> bool:
    """
    Validate contract prices (YES + NO = 1.00).
    
    Args:
        df: DataFrame with contract prices
        
    Returns:
        True if valid, raises ValueError otherwise
    """
    price_sum = df['yes_price'] + df['no_price']
    tolerance = 0.01
    
    if not np.allclose(price_sum, 1.0, atol=tolerance):
        invalid = df[~np.isclose(price_sum, 1.0, atol=tolerance)]
        raise ValueError(
            f"YES + NO must equal 1.00. Found {len(invalid)} invalid rows. "
            f"Example: YES={invalid.iloc[0]['yes_price']}, NO={invalid.iloc[0]['no_price']}"
        )
    
    print("Contract price validation passed ✓")
    return True


def main():
    """Main entry point for Kalshi data collection."""
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    btc_prices_file = os.getenv('BTC_PRICES_FILE', 'data/btc_prices_minute.csv')
    markets_file = os.getenv('KALSHI_MARKETS_FILE', 'data/kalshi_markets.csv')
    contract_prices_file = os.getenv('KALSHI_CONTRACT_PRICES_FILE', 'data/kalshi_contract_prices.csv')
    
    print("=" * 60)
    print("Kalshi Market Data Generation")
    print("=" * 60)
    print(f"Input: {btc_prices_file}")
    print(f"Output Markets: {markets_file}")
    print(f"Output Prices: {contract_prices_file}")
    print()
    
    try:
        # Load BTC prices
        print("Loading BTC prices...")
        btc_df = load_btc_prices(btc_prices_file)
        print(f"Loaded {len(btc_df)} BTC price records")
        
        # Filter for today only
        today_btc = get_todays_btc_prices(btc_df)
        print(f"Today's data: {len(today_btc)} records")
        
        if today_btc.empty:
            print("No BTC data for today. Please run collect_btc_prices.py first.")
            return
        
        # Generate hourly markets
        print("\nGenerating hourly markets...")
        markets_df = generate_hourly_markets(today_btc)
        print(f"Generated {len(markets_df)} markets")
        
        # Show sample
        print("\nSample markets:")
        print(markets_df.head(10))
        
        # Append markets to CSV
        print()
        append_to_csv(markets_df, markets_file, ['hour_start', 'strike_price'])
        
        # Generate contract prices
        print("\nGenerating contract prices...")
        contract_prices_df = generate_contract_prices(today_btc, markets_df)
        print(f"Generated {len(contract_prices_df)} price records")
        
        # Validate
        validate_contract_prices(contract_prices_df)
        
        # Show sample
        print("\nSample contract prices:")
        print(contract_prices_df.head())
        
        # Append to CSV
        print()
        append_to_csv(contract_prices_df, contract_prices_file, 
                     ['timestamp', 'strike_price'])
        
        print("\n✓ Kalshi data generation completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
