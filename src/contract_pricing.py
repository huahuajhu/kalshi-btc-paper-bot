"""Contract pricing simulation for YES/NO prices."""

import numpy as np
import pandas as pd
from scipy.stats import norm


class ContractPricer:
    """Simulate YES/NO contract prices based on BTC price movements."""
    
    def __init__(self, volatility: float = 0.02):
        """
        Initialize contract pricer.
        
        Args:
            volatility: Price volatility parameter for pricing (default: 0.02)
        """
        self.volatility = volatility
    
    def calculate_yes_probability(self, 
                                  current_price: float,
                                  strike_price: float,
                                  time_to_expiry_hours: float) -> float:
        """
        Calculate the probability that BTC price will be >= strike at expiry.
        
        Uses a simplified Black-Scholes-like approach.
        
        Args:
            current_price: Current BTC price
            strike_price: Strike price of the market
            time_to_expiry_hours: Hours until market expiry
            
        Returns:
            Probability (0 to 1) that BTC >= strike
        """
        if time_to_expiry_hours <= 0:
            # At expiry, deterministic outcome
            return 1.0 if current_price >= strike_price else 0.0
        
        # Convert hours to fraction of year (approx)
        time_years = time_to_expiry_hours / (365.25 * 24)
        
        if current_price <= 0 or strike_price <= 0:
            return 0.5  # Default to 50/50 if prices invalid
        
        # Calculate d2 from Black-Scholes
        d2 = (np.log(current_price / strike_price)) / (self.volatility * np.sqrt(time_years))
        
        # Probability of being above strike
        prob = norm.cdf(d2)
        
        # Clamp to reasonable range
        return np.clip(prob, 0.01, 0.99)
    
    def get_yes_no_prices(self,
                         current_price: float,
                         strike_price: float,
                         time_to_expiry_hours: float,
                         spread: float = 0.0) -> tuple[float, float]:
        """
        Get YES and NO contract prices.
        
        Args:
            current_price: Current BTC price
            strike_price: Strike price of the market
            time_to_expiry_hours: Hours until expiry
            spread: Bid-ask spread (default: 0.0)
            
        Returns:
            Tuple of (yes_price, no_price) where yes_price + no_price ≈ 1.00
        """
        # Calculate fair probability
        yes_prob = self.calculate_yes_probability(
            current_price, strike_price, time_to_expiry_hours
        )
        
        # Apply small spread if needed
        yes_price = np.clip(yes_prob + spread / 2, 0.01, 0.99)
        
        # Ensure YES + NO = 1.00 (no market maker profit in simulation)
        no_price = 1.0 - yes_price
        
        return yes_price, no_price
    
    def simulate_contract_prices(self,
                                btc_prices: pd.DataFrame,
                                strike_price: float,
                                hour_start: pd.Timestamp,
                                hour_end: pd.Timestamp) -> pd.DataFrame:
        """
        Simulate YES/NO prices for an entire hour.
        
        Args:
            btc_prices: DataFrame with minute-by-minute BTC prices
            strike_price: Strike price for this market
            hour_start: Start of the hour
            hour_end: End of the hour
            
        Returns:
            DataFrame with timestamp, yes_price, no_price columns
        """
        # Filter prices for this hour
        mask = (btc_prices.index >= hour_start) & (btc_prices.index < hour_end)
        hour_prices = btc_prices[mask].copy()
        
        if hour_prices.empty:
            return pd.DataFrame(columns=['timestamp', 'yes_price', 'no_price'])
        
        results = []
        for timestamp, row in hour_prices.iterrows():
            # Calculate time remaining in hours
            time_remaining = (hour_end - timestamp).total_seconds() / 3600
            
            # Get YES/NO prices
            yes_price, no_price = self.get_yes_no_prices(
                current_price=row['price'],
                strike_price=strike_price,
                time_to_expiry_hours=time_remaining
            )
            
            results.append({
                'timestamp': timestamp,
                'yes_price': yes_price,
                'no_price': no_price
            })
        
        return pd.DataFrame(results)
