"""Dataset factory for creating ML-ready datasets from simulator data."""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from pathlib import Path


class DatasetFactory:
    """
    Convert simulator data into ML-ready datasets.
    
    Creates features like:
    - btc_return_5m: BTC return over last 5 minutes
    - btc_return_15m: BTC return over last 15 minutes
    - yes_price: Current YES contract price
    - no_price: Current NO contract price
    - spread: Difference between YES and NO prices
    - volatility: Rolling volatility of BTC returns
    - label: Binary outcome (1 if BTC >= strike, 0 otherwise)
    """
    
    def __init__(self, lookback_5m: int = 5, lookback_15m: int = 15, 
                 volatility_window: int = 10):
        """
        Initialize dataset factory.
        
        Args:
            lookback_5m: Minutes to look back for 5-minute return (default: 5)
            lookback_15m: Minutes to look back for 15-minute return (default: 15)
            volatility_window: Window for rolling volatility calculation (default: 10)
        """
        self.lookback_5m = lookback_5m
        self.lookback_15m = lookback_15m
        self.volatility_window = volatility_window
        self.dataset_rows = []
        
    def reset(self):
        """Reset the dataset collector."""
        self.dataset_rows = []
    
    def collect_minute_data(self,
                           timestamp: pd.Timestamp,
                           btc_price: float,
                           yes_price: float,
                           no_price: float,
                           strike_price: float,
                           hour_start: pd.Timestamp,
                           btc_history: List[float]) -> None:
        """
        Collect data for a single minute during simulation.
        
        Args:
            timestamp: Current timestamp
            btc_price: Current BTC price
            yes_price: Current YES contract price
            no_price: Current NO contract price
            strike_price: Strike price of the market
            hour_start: Start time of the market hour (for unique identification)
            btc_history: List of recent BTC prices (for computing returns)
        """
        # Calculate BTC returns
        btc_return_5m = self._calculate_return(btc_history, self.lookback_5m)
        btc_return_15m = self._calculate_return(btc_history, self.lookback_15m)
        
        # Calculate spread (difference between YES and NO prices)
        # Note: In Kalshi markets, YES + NO = 1.0, so spread shows market sentiment asymmetry
        spread = abs(yes_price - no_price)
        
        # Calculate volatility
        volatility = self._calculate_volatility(btc_history, self.volatility_window)
        
        # Store row (label will be added at market resolution)
        row = {
            'timestamp': timestamp,
            'hour_start': hour_start,
            'btc_price': btc_price,
            'btc_return_5m': btc_return_5m,
            'btc_return_15m': btc_return_15m,
            'yes_price': yes_price,
            'no_price': no_price,
            'spread': spread,
            'volatility': volatility,
            'strike_price': strike_price,
            'label': None  # Will be filled at resolution
        }
        
        self.dataset_rows.append(row)
    
    def add_labels(self, final_btc_price: float, strike_price: float,
                   hour_start: pd.Timestamp) -> None:
        """
        Add labels to all collected rows for a market based on final outcome.
        
        Args:
            final_btc_price: Final BTC price at market resolution
            strike_price: Strike price of the market
            hour_start: Start time of the market hour (for unique identification)
        """
        # Label is 1 if BTC >= strike (YES wins), 0 otherwise (NO wins)
        label = 1 if final_btc_price >= strike_price else 0
        
        # Apply label to all rows from this specific market
        for row in self.dataset_rows:
            if (row['strike_price'] == strike_price and 
                row['hour_start'] == hour_start and 
                row['label'] is None):
                row['label'] = label
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert collected data to a pandas DataFrame.
        
        Returns:
            DataFrame with ML-ready features and labels
        """
        if not self.dataset_rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.dataset_rows)
        
        # Drop rows with missing labels or features
        df = df.dropna()
        
        # Reorder columns to match example schema
        columns_order = [
            'timestamp',
            'btc_price',
            'btc_return_5m',
            'btc_return_15m',
            'yes_price',
            'no_price',
            'spread',
            'volatility',
            'strike_price',
            'label'
        ]
        
        # Only include columns that exist
        columns_order = [col for col in columns_order if col in df.columns]
        df = df[columns_order]
        
        return df
    
    def get_feature_columns(self) -> List[str]:
        """
        Get list of feature column names (excluding metadata and labels).
        
        Returns:
            List of feature column names
        """
        return [
            'btc_return_5m',
            'btc_return_15m',
            'yes_price',
            'no_price',
            'spread',
            'volatility'
        ]
    
    def save_csv(self, output_path: str) -> None:
        """
        Save dataset to CSV file.
        
        Args:
            output_path: Path to save the CSV file
        """
        df = self.to_dataframe()
        
        if df.empty:
            print(f"Warning: No data to save to {output_path}")
            return
        
        # Create directory if it doesn't exist
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to CSV
        df.to_csv(output_path, index=False)
        print(f"Dataset saved to {output_path} ({len(df)} rows)")
    
    def _calculate_return(self, price_history: List[float], 
                         lookback: int) -> Optional[float]:
        """
        Calculate percentage return over lookback period.
        
        Args:
            price_history: List of historical prices
            lookback: Number of periods to look back
            
        Returns:
            Percentage return, or None if insufficient data
        """
        if len(price_history) < lookback + 1:
            return None
        
        current_price = price_history[-1]
        past_price = price_history[-(lookback + 1)]
        
        if past_price == 0:
            return None
        
        return (current_price - past_price) / past_price
    
    def _calculate_volatility(self, price_history: List[float],
                             window: int) -> Optional[float]:
        """
        Calculate rolling volatility (standard deviation of returns).
        
        Args:
            price_history: List of historical prices
            window: Window size for volatility calculation
            
        Returns:
            Volatility (std of returns), or None if insufficient data
        """
        if len(price_history) < window + 1:
            return None
        
        # Get recent prices
        recent_prices = price_history[-(window + 1):]
        
        # Calculate returns
        returns = []
        for i in range(1, len(recent_prices)):
            if recent_prices[i-1] != 0:
                ret = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                returns.append(ret)
        
        if not returns:
            return None
        
        # Return standard deviation of returns
        return np.std(returns)
