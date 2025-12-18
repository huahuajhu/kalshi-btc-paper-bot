"""
Collect today's BTC minute-level price data from public crypto exchanges.

Uses CCXT library to fetch OHLCV data from Binance or Coinbase.
Data is validated and appended to btc_prices_minute.csv.
"""

import ccxt
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import sys

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_exchange(exchange_name: str = "binance"):
    """
    Initialize and return exchange object.
    
    Args:
        exchange_name: Name of exchange ('binance' or 'coinbase')
        
    Returns:
        CCXT exchange object
    """
    exchange_name = exchange_name.lower()
    
    if exchange_name == "binance":
        exchange = ccxt.binance({
            'enableRateLimit': True,
        })
    elif exchange_name == "coinbase":
        exchange = ccxt.coinbase({
            'enableRateLimit': True,
        })
    else:
        raise ValueError(f"Unsupported exchange: {exchange_name}")
    
    return exchange


def fetch_btc_prices_today(exchange_name: str = "binance") -> pd.DataFrame:
    """
    Fetch today's BTC/USDT minute-level prices.
    
    Args:
        exchange_name: Exchange to use ('binance' or 'coinbase')
        
    Returns:
        DataFrame with columns: timestamp, price
    """
    print(f"Fetching BTC prices from {exchange_name}...")
    
    exchange = get_exchange(exchange_name)
    
    # Get today's date range (UTC)
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
    
    # Convert to milliseconds since epoch
    since = int(today_start.timestamp() * 1000)
    
    # Fetch OHLCV data (1 minute candles)
    symbol = 'BTC/USDT'
    timeframe = '1m'
    
    print(f"Fetching {symbol} {timeframe} data since {today_start} UTC...")
    
    all_candles = []
    limit = 1000  # Maximum candles per request
    
    while True:
        try:
            candles = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=limit
            )
            
            if not candles:
                break
            
            all_candles.extend(candles)
            
            # Update since to last candle timestamp + 1 minute
            last_timestamp = candles[-1][0]
            since = last_timestamp + 60000  # 1 minute in milliseconds
            
            # Stop if we've reached current time
            if last_timestamp >= int(now.timestamp() * 1000):
                break
            
            print(f"Fetched {len(candles)} candles, total: {len(all_candles)}")
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            break
    
    if not all_candles:
        print("No data fetched")
        return pd.DataFrame(columns=['timestamp', 'price'])
    
    # Convert to DataFrame
    # OHLCV format: [timestamp, open, high, low, close, volume]
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Use close price as the price
    df = df[['timestamp', 'close']].rename(columns={'close': 'price'})
    
    # Convert timestamp from milliseconds to datetime string
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"Fetched {len(df)} minute-level prices for today")
    
    return df


def append_to_csv(new_data: pd.DataFrame, filepath: str):
    """
    Append new data to existing CSV file, avoiding duplicates.
    
    Args:
        new_data: DataFrame with new data
        filepath: Path to CSV file
    """
    filepath = Path(filepath)
    
    if new_data.empty:
        print("No new data to append")
        return
    
    # Ensure data directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing data if file exists
    if filepath.exists():
        print(f"Loading existing data from {filepath}...")
        existing_data = pd.read_csv(filepath)
        
        # Combine and remove duplicates based on timestamp
        combined = pd.concat([existing_data, new_data], ignore_index=True)
        combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
        combined = combined.sort_values('timestamp')
        
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


def validate_data(df: pd.DataFrame) -> bool:
    """
    Validate BTC price data format and content.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        True if valid, raises ValueError otherwise
    """
    # Check required columns
    if not all(col in df.columns for col in ['timestamp', 'price']):
        raise ValueError("Data must have 'timestamp' and 'price' columns")
    
    # Check for null values
    if df.isnull().any().any():
        raise ValueError("Data contains null values")
    
    # Check price values are positive
    if (df['price'] <= 0).any():
        raise ValueError("Price values must be positive")
    
    # Validate timestamp format
    try:
        pd.to_datetime(df['timestamp'])
    except Exception as e:
        raise ValueError(f"Invalid timestamp format: {e}")
    
    print("Data validation passed ✓")
    return True


def main():
    """Main entry point for BTC price collection."""
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    exchange_name = os.getenv('BTC_EXCHANGE', 'binance')
    btc_prices_file = os.getenv('BTC_PRICES_FILE', 'data/btc_prices_minute.csv')
    
    print("=" * 60)
    print("BTC Price Data Collection")
    print("=" * 60)
    print(f"Exchange: {exchange_name}")
    print(f"Output file: {btc_prices_file}")
    print()
    
    try:
        # Fetch today's data
        df = fetch_btc_prices_today(exchange_name)
        
        if df.empty:
            print("No data to save")
            return
        
        # Validate data
        validate_data(df)
        
        # Show sample
        print("\nSample data (first 5 rows):")
        print(df.head())
        
        # Append to CSV
        print()
        append_to_csv(df, btc_prices_file)
        
        print("\n✓ BTC price collection completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
