"""Market selector for choosing the closest strike price."""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
import csv
import os


class MarketSelector:
    """Select the appropriate market based on current BTC price at hour start."""
    
    def __init__(self, btc_price_interval: int = 250, log_path: str = "data/market_selection_log.csv"):
        """
        Initialize market selector.
        
        Args:
            btc_price_interval: Price interval for market buckets (default: $250)
            log_path: Path to save market selection log
        """
        self.btc_price_interval = btc_price_interval
        self.log_path = log_path
        self.selection_log = []
        
        # Initialize log file
        self._init_log_file()
    
    def _init_log_file(self):
        """Initialize the market selection log CSV file."""
        os.makedirs(os.path.dirname(self.log_path) if os.path.dirname(self.log_path) else '.', exist_ok=True)
        with open(self.log_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'hour_start', 'btc_spot_price', 'selected_strike', 'selection_method',
                'avg_spread', 'avg_volume_proxy', 'price_reaction_score', 'volatility_estimate',
                'num_strikes_considered', 'reason'
            ])
    
    def _calculate_market_metrics(self, 
                                  hour_start: pd.Timestamp,
                                  strike_price: float,
                                  contract_prices: pd.DataFrame,
                                  btc_prices: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate metrics for a specific market (strike).
        
        Metrics include:
        - Spread: Avg difference between YES + NO prices and 1.0
        - Volume proxy: Count of price changes (more changes = more trading activity)
        - Price reaction: Correlation between BTC price changes and contract price changes
        
        Args:
            hour_start: Start of the trading hour
            strike_price: Strike price to analyze
            contract_prices: DataFrame with contract prices
            btc_prices: DataFrame with BTC prices
            
        Returns:
            Dictionary with metrics
        """
        hour_end = hour_start + pd.Timedelta(hours=1)
        
        # Filter contract prices for this hour and strike
        mask = (
            (contract_prices['timestamp'] >= hour_start) &
            (contract_prices['timestamp'] < hour_end) &
            (contract_prices['strike_price'] == strike_price)
        )
        hour_contracts = contract_prices[mask].copy()
        
        if hour_contracts.empty or len(hour_contracts) < 2:
            return {
                'avg_spread': 1.0,  # Worst spread
                'volume_proxy': 0.0,
                'price_reaction': 0.0
            }
        
        # Calculate spread (lower is better)
        hour_contracts['spread'] = abs(
            (hour_contracts['yes_price'] + hour_contracts['no_price']) - 1.0
        )
        avg_spread = hour_contracts['spread'].mean()
        
        # Calculate volume proxy (more price changes = more activity)
        yes_changes = hour_contracts['yes_price'].diff().abs().sum()
        no_changes = hour_contracts['no_price'].diff().abs().sum()
        volume_proxy = yes_changes + no_changes
        
        # Calculate price reaction to BTC movements
        # Merge with BTC prices
        hour_btc = btc_prices[
            (btc_prices.index >= hour_start) & 
            (btc_prices.index < hour_end)
        ].copy()
        
        if len(hour_btc) < 2:
            price_reaction = 0.0
        else:
            # Align timestamps
            hour_contracts_indexed = hour_contracts.set_index('timestamp')
            common_times = hour_contracts_indexed.index.intersection(hour_btc.index)
            
            if len(common_times) < 2:
                price_reaction = 0.0
            else:
                btc_changes = hour_btc.loc[common_times, 'price'].diff()
                yes_changes_aligned = hour_contracts_indexed.loc[common_times, 'yes_price'].diff()
                
                # Calculate correlation (higher absolute correlation = more reactive)
                if btc_changes.std() > 0 and yes_changes_aligned.std() > 0:
                    price_reaction = abs(btc_changes.corr(yes_changes_aligned))
                else:
                    price_reaction = 0.0
        
        return {
            'avg_spread': avg_spread,
            'volume_proxy': volume_proxy,
            'price_reaction': price_reaction
        }
    
    def _estimate_volatility(self, btc_prices: pd.DataFrame, lookback_hours: int = 24) -> float:
        """
        Estimate BTC price volatility based on recent price movements.
        
        Args:
            btc_prices: DataFrame with BTC prices
            lookback_hours: Number of hours to look back (default: 24)
            
        Returns:
            Volatility estimate (standard deviation of returns)
        """
        if len(btc_prices) < 2:
            return 0.02  # Default volatility
        
        # Get last N hours of data
        recent_prices = btc_prices.tail(lookback_hours * 60)  # 60 minutes per hour
        
        if len(recent_prices) < 2:
            return 0.02
        
        # Calculate returns
        returns = recent_prices['price'].pct_change().dropna()
        
        if len(returns) == 0:
            return 0.02
        
        # Return standard deviation of returns
        return returns.std()
    
    def select_intelligent_strike(self,
                                  hour_start: pd.Timestamp,
                                  btc_spot_price: float,
                                  available_strikes: List[float],
                                  contract_prices: pd.DataFrame,
                                  btc_prices: pd.DataFrame,
                                  min_volume_threshold: float = 0.01) -> Dict:
        """
        Select the best strike based on multiple factors.
        
        Selection criteria (in order of priority):
        1. Filter out low-liquidity markets (volume_proxy < threshold)
        2. Among liquid markets, prefer:
           - Tighter spreads (lower avg_spread)
           - Higher volume (higher volume_proxy)
           - Better price reaction (higher price_reaction)
        3. Consider volatility to choose appropriate strike distance
        
        Args:
            hour_start: Start of the trading hour
            btc_spot_price: Current BTC spot price
            available_strikes: List of available strike prices
            contract_prices: DataFrame with contract prices
            btc_prices: DataFrame with BTC prices
            min_volume_threshold: Minimum volume proxy to consider a market liquid
            
        Returns:
            Dictionary with selected strike and selection rationale
        """
        if not available_strikes:
            raise ValueError("No available strikes to select from")
        
        # Estimate current volatility
        volatility = self._estimate_volatility(btc_prices)
        
        # Calculate metrics for each strike
        strike_metrics = []
        for strike in available_strikes:
            metrics = self._calculate_market_metrics(
                hour_start, strike, contract_prices, btc_prices
            )
            metrics['strike_price'] = strike
            metrics['distance_from_spot'] = abs(strike - btc_spot_price)
            strike_metrics.append(metrics)
        
        # Convert to DataFrame for easier analysis
        metrics_df = pd.DataFrame(strike_metrics)
        
        # Filter out low-liquidity markets
        liquid_markets = metrics_df[metrics_df['volume_proxy'] >= min_volume_threshold]
        
        if liquid_markets.empty:
            # Fallback to closest strike if no liquid markets
            selected_strike = min(available_strikes, key=lambda x: abs(x - btc_spot_price))
            selected_metrics = metrics_df[metrics_df['strike_price'] == selected_strike].iloc[0]
            
            return {
                'strike_price': selected_strike,
                'method': 'fallback_closest',
                'reason': 'No liquid markets found, using closest strike',
                'metrics': selected_metrics.to_dict()
            }
        
        # Score each liquid market
        # Lower spread is better, higher volume is better, higher reaction is better
        liquid_markets = liquid_markets.copy()
        
        # Normalize metrics (0-1 scale)
        if liquid_markets['avg_spread'].max() > 0:
            liquid_markets['spread_score'] = 1 - (
                liquid_markets['avg_spread'] / liquid_markets['avg_spread'].max()
            )
        else:
            liquid_markets['spread_score'] = 1.0
        
        if liquid_markets['volume_proxy'].max() > 0:
            liquid_markets['volume_score'] = (
                liquid_markets['volume_proxy'] / liquid_markets['volume_proxy'].max()
            )
        else:
            liquid_markets['volume_score'] = 0.5
        
        if liquid_markets['price_reaction'].max() > 0:
            liquid_markets['reaction_score'] = (
                liquid_markets['price_reaction'] / liquid_markets['price_reaction'].max()
            )
        else:
            liquid_markets['reaction_score'] = 0.5
        
        # Combine scores (weighted average)
        # Spread: 40%, Volume: 30%, Reaction: 30%
        liquid_markets['total_score'] = (
            0.4 * liquid_markets['spread_score'] +
            0.3 * liquid_markets['volume_score'] +
            0.3 * liquid_markets['reaction_score']
        )
        
        # Select the strike with highest total score
        best_market = liquid_markets.loc[liquid_markets['total_score'].idxmax()]
        
        return {
            'strike_price': best_market['strike_price'],
            'method': 'intelligent_selection',
            'reason': f"Best score: spread={best_market['spread_score']:.2f}, volume={best_market['volume_score']:.2f}, reaction={best_market['reaction_score']:.2f}",
            'metrics': best_market.to_dict(),
            'volatility': volatility,
            'num_strikes_considered': len(available_strikes),
            'num_liquid_strikes': len(liquid_markets)
        }
    
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
                           markets_df: pd.DataFrame,
                           contract_prices_df: pd.DataFrame = None,
                           use_intelligent_selection: bool = True) -> Optional[dict]:
        """
        Get the selected market for a specific hour.
        
        Rules:
        - At hour start, take BTC spot price
        - Select strike price using intelligent selection (or closest if disabled)
        - Return selected strike for that hour
        
        Args:
            hour_start: Start of the trading hour
            btc_prices_df: DataFrame with BTC prices (indexed by timestamp)
            markets_df: DataFrame of available markets
            contract_prices_df: DataFrame with contract prices (required for intelligent selection)
            use_intelligent_selection: Whether to use intelligent selection (default: True)
            
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
        
        # Select strike
        if use_intelligent_selection and contract_prices_df is not None:
            # Use intelligent selection
            selection_result = self.select_intelligent_strike(
                hour_start=hour_start,
                btc_spot_price=btc_spot_price,
                available_strikes=available_strikes,
                contract_prices=contract_prices_df,
                btc_prices=btc_prices_df
            )
            selected_strike = selection_result['strike_price']
            
            # Log the selection
            self._log_selection(
                hour_start=hour_start,
                btc_spot_price=btc_spot_price,
                selection_result=selection_result
            )
        else:
            # Fallback to closest strike
            selected_strike = self.select_closest_strike(btc_spot_price, available_strikes)
            
            # Log the fallback selection
            self._log_selection(
                hour_start=hour_start,
                btc_spot_price=btc_spot_price,
                selection_result={
                    'strike_price': selected_strike,
                    'method': 'closest_strike',
                    'reason': 'Intelligent selection disabled or no contract prices',
                    'metrics': {},
                    'volatility': 0.0,
                    'num_strikes_considered': len(available_strikes)
                }
            )
        
        # Get the selected market
        selected_market = hour_markets[hour_markets['strike_price'] == selected_strike].iloc[0]
        
        return {
            'hour_start': selected_market['hour_start'],
            'hour_end': selected_market['hour_end'],
            'strike_price': selected_strike,
            'btc_spot_price': btc_spot_price
        }
    
    def _log_selection(self, hour_start: pd.Timestamp, btc_spot_price: float, selection_result: Dict):
        """Log market selection to CSV file."""
        metrics = selection_result.get('metrics', {})
        volatility = selection_result.get('volatility', 0.0)
        
        log_entry = [
            hour_start,
            btc_spot_price,
            selection_result['strike_price'],
            selection_result.get('method', 'unknown'),
            metrics.get('avg_spread', 0.0),
            metrics.get('volume_proxy', 0.0),
            metrics.get('price_reaction', 0.0),
            volatility,
            selection_result.get('num_strikes_considered', 0),
            selection_result.get('reason', '')
        ]
        
        # Append to log file
        with open(self.log_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(log_entry)
        
        # Also keep in memory for analysis
        self.selection_log.append({
            'hour_start': hour_start,
            'btc_spot_price': btc_spot_price,
            'selected_strike': selection_result['strike_price'],
            'method': selection_result.get('method', 'unknown'),
            'metrics': metrics,
            'volatility': volatility
        })
    
    def get_selection_summary(self) -> pd.DataFrame:
        """
        Get summary statistics of market selections.
        
        Returns:
            DataFrame with selection summary
        """
        if not self.selection_log:
            return pd.DataFrame()
        
        # Extract metrics from in-memory log
        spreads = []
        volumes = []
        reactions = []
        volatilities = []
        
        for entry in self.selection_log:
            metrics = entry.get('metrics', {})
            spreads.append(metrics.get('avg_spread', 0.0))
            volumes.append(metrics.get('volume_proxy', 0.0))
            reactions.append(metrics.get('price_reaction', 0.0))
            volatilities.append(entry.get('volatility', 0.0))
        
        # Count intelligent vs fallback selections
        intelligent_count = sum(1 for entry in self.selection_log if entry.get('method') == 'intelligent_selection')
        fallback_count = len(self.selection_log) - intelligent_count
        
        summary = {
            'total_selections': len(self.selection_log),
            'intelligent_selections': intelligent_count,
            'fallback_selections': fallback_count,
            'avg_spread': np.mean(spreads) if spreads else 0.0,
            'avg_volume_proxy': np.mean(volumes) if volumes else 0.0,
            'avg_price_reaction': np.mean(reactions) if reactions else 0.0,
            'avg_volatility': np.mean(volatilities) if volatilities else 0.0
        }
        
        return pd.DataFrame([summary])
    
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
