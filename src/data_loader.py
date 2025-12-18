"""Data loader for BTC prices and Kalshi market data."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional


class DataLoader:
    """Load and preprocess data for the simulator with validation."""
    
    def __init__(self, 
                 btc_prices_path: str,
                 markets_path: str,
                 contract_prices_path: str):
        """Initialize data loader with file paths."""
        self.btc_prices_path = Path(btc_prices_path)
        self.markets_path = Path(markets_path)
        self.contract_prices_path = Path(contract_prices_path)
        
    def load_btc_prices(self, 
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Load minute-level BTC prices with validation.
        
        Expected columns: timestamp, price
        
        Args:
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            
        Returns:
            DataFrame with timestamp index and price column
            
        Raises:
            ValueError: If data validation fails
        """
        if not self.btc_prices_path.exists():
            raise FileNotFoundError(f"BTC prices file not found: {self.btc_prices_path}")
        
        df = pd.read_csv(self.btc_prices_path)
        
        # Validate required columns
        if 'timestamp' not in df.columns or 'price' not in df.columns:
            raise ValueError("BTC prices CSV must have 'timestamp' and 'price' columns")
        
        # Parse and validate timestamps
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Validate prices
        if (df['price'] <= 0).any():
            raise ValueError("BTC prices must be positive")
        
        # Set index and sort
        df = df.set_index('timestamp').sort_index()
        
        # Check for duplicate timestamps
        if df.index.duplicated().any():
            raise ValueError("Duplicate timestamps found in BTC prices")
        
        # Filter by date range
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
            
        return df
    
    def load_markets(self) -> pd.DataFrame:
        """
        Load Kalshi hourly market strikes with validation.
        
        Expected columns: hour_start, strike_price
        
        Returns:
            DataFrame with market information including computed hour_end
            
        Raises:
            ValueError: If data validation fails
        """
        if not self.markets_path.exists():
            raise FileNotFoundError(f"Markets file not found: {self.markets_path}")
        
        df = pd.read_csv(self.markets_path)
        
        # Validate required columns
        if 'hour_start' not in df.columns or 'strike_price' not in df.columns:
            raise ValueError("Markets CSV must have 'hour_start' and 'strike_price' columns")
        
        # Parse timestamps
        df['hour_start'] = pd.to_datetime(df['hour_start'])
        
        # Validate strike prices
        if (df['strike_price'] <= 0).any():
            raise ValueError("Strike prices must be positive")
        
        # Add hour_end (1 hour after start)
        df['hour_end'] = df['hour_start'] + pd.Timedelta(hours=1)
        
        return df
    
    def load_contract_prices(self) -> pd.DataFrame:
        """
        Load minute-level YES/NO prices with validation.
        
        Expected columns: timestamp, strike_price, yes_price, no_price
        
        Returns:
            DataFrame with contract pricing information
            
        Raises:
            ValueError: If data validation fails or YES + NO ≠ 1
        """
        if not self.contract_prices_path.exists():
            raise FileNotFoundError(f"Contract prices file not found: {self.contract_prices_path}")
        
        df = pd.read_csv(self.contract_prices_path)
        
        # Validate required columns
        required_cols = ['timestamp', 'strike_price', 'yes_price', 'no_price']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Contract prices CSV must have columns: {required_cols}")
        
        # Parse timestamps
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Validate price bounds (0 < price < 1)
        if ((df['yes_price'] < 0) | (df['yes_price'] > 1)).any():
            raise ValueError("YES prices must be between 0 and 1")
        if ((df['no_price'] < 0) | (df['no_price'] > 1)).any():
            raise ValueError("NO prices must be between 0 and 1")
        
        # Validate YES + NO ≈ 1.00 (allow small floating point error)
        price_sum = df['yes_price'] + df['no_price']
        tolerance = 0.01  # 1 cent tolerance
        if not np.allclose(price_sum, 1.0, atol=tolerance):
            invalid_rows = df[~np.isclose(price_sum, 1.0, atol=tolerance)]
            raise ValueError(
                f"YES + NO must ≈ 1.00. Found {len(invalid_rows)} invalid rows. "
                f"Example: YES={invalid_rows.iloc[0]['yes_price']}, "
                f"NO={invalid_rows.iloc[0]['no_price']}"
            )
        
        return df
