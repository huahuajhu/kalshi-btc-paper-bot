"""Market selector for choosing the closest strike price."""

import pandas as pd
from typing import Optional


class MarketSelector:
    """Select the appropriate market based on current BTC price at hour start."""
    
    def __init__(self, btc_price_interval: int = 250):
        """
        Initialize market selector.
        
        Args:
            btc_price_interval: Price interval for market buckets (default: $250)
        """
        self.btc_price_interval = btc_price_interval
    
    def select_closest_strike(self, btc_spot_price: float, available_strikes: list[float]) -> float:
        """
        Select the closest strike price to the current BTC spot price.
        
        Rules:
        - At hour start, take BTC spot price
        - Select strike price closest to BTC price
        
        Args:
            btc_spot_price: Current BTC spot price at hour start
            available_strikes: List of available strike prices
            
        Returns:
            Closest strike price
            
        Raises:
            ValueError: If no strikes available
        """
        if not available_strikes:
            raise ValueError("No available strikes to select from")
        
        # Find the strike with minimum absolute difference
        closest_strike = min(available_strikes, key=lambda x: abs(x - btc_spot_price))
        return closest_strike
    
    def get_market_for_hour(self, 
                           hour_start: pd.Timestamp,
                           btc_prices_df: pd.DataFrame,
                           markets_df: pd.DataFrame) -> Optional[dict]:
        """
        Get the selected market for a specific hour.
        
        Rules:
        - At hour start, take BTC spot price
        - Select strike price closest to BTC price
        - Return selected strike for that hour
        
        Args:
            hour_start: Start of the trading hour
            btc_prices_df: DataFrame with BTC prices (indexed by timestamp)
            markets_df: DataFrame of available markets
            
        Returns:
            Dictionary with market info: {hour_start, hour_end, strike_price, btc_spot_price}
            Returns None if no market found or no BTC price at hour start
        """
        # Get BTC spot price at hour start
        if hour_start not in btc_prices_df.index:
            return None
        
        btc_spot_price = btc_prices_df.loc[hour_start, 'price']
        
        # Filter markets for this specific hour
        hour_markets = markets_df[markets_df['hour_start'] == hour_start]
        
        if hour_markets.empty:
            return None
        
        # Get available strikes
        available_strikes = hour_markets['strike_price'].tolist()
        
        # Select closest strike
        selected_strike = self.select_closest_strike(btc_spot_price, available_strikes)
        
        # Get the selected market
        selected_market = hour_markets[hour_markets['strike_price'] == selected_strike].iloc[0]
        
        return {
            'hour_start': selected_market['hour_start'],
            'hour_end': selected_market['hour_end'],
            'strike_price': selected_strike,
            'btc_spot_price': btc_spot_price
        }
    
    def generate_strikes_around_price(self, price: float, num_strikes: int = 5) -> list[float]:
        """
        Generate strike prices around a given price.
        
        Args:
            price: Current price
            num_strikes: Number of strikes to generate on each side
            
        Returns:
            List of strike prices
        """
        # Round to nearest strike interval
        base_strike = round(price / self.btc_price_interval) * self.btc_price_interval
        
        strikes = []
        for i in range(-num_strikes, num_strikes + 1):
            strikes.append(base_strike + i * self.btc_price_interval)
        
        return sorted(strikes)
