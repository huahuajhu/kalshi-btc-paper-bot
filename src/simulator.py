"""Main simulator for paper trading."""

import pandas as pd
from typing import Dict, Optional
from .config import SimulationConfig
from .data_loader import DataLoader
from .market_selector import MarketSelector
from .contract_pricing import ContractPricer
from .portfolio import Portfolio
from .market_microstructure import MarketMicrostructure
from .strategies.base import Strategy, TradeAction
from .dataset_factory import DatasetFactory
from .explainability import ExplainabilityEngine


class Simulator:
    """
    Simulator that:
    - loops over each hour
    - selects the market at hour start
    - iterates minute-by-minute for 60 minutes
    - feeds prices to the strategy
    - executes paper trades
    - resolves market at hour end
    - records PnL
    """
    
    def __init__(self, config: SimulationConfig):
        """
        Initialize simulator.
        
        Args:
            config: Simulation configuration
        """
        self.config = config
        self.data_loader = DataLoader(
            btc_prices_path=config.btc_prices_path,
            markets_path=config.markets_path,
            contract_prices_path=config.contract_prices_path
        )
        self.market_selector = MarketSelector(
            btc_price_interval=config.btc_price_interval
        )
        self.contract_pricer = ContractPricer()
        self.dataset_factory = None  # Optional dataset collector
        
    def run(self, strategy: Strategy, collect_dataset: bool = False) -> Dict:
        """
        Run simulation with a given strategy.
        
        Args:
            strategy: Trading strategy to use
            collect_dataset: If True, collect ML-ready dataset during simulation
            
        Returns:
            Dictionary with simulation results
        """
        # Initialize dataset factory if requested
        if collect_dataset:
            self.dataset_factory = DatasetFactory()
        
        # Load data
        btc_prices = self.data_loader.load_btc_prices(
            start_date=self.config.start_date,
            end_date=self.config.end_date
        )
        markets = self.data_loader.load_markets()
        contract_prices = self.data_loader.load_contract_prices()
        
        # Initialize market microstructure
        market_microstructure = MarketMicrostructure(
            bid_ask_spread=self.config.bid_ask_spread,
            slippage_per_100_contracts=self.config.slippage_per_100_contracts,
            max_liquidity_per_minute=self.config.max_liquidity_per_minute,
            latency_minutes=self.config.latency_minutes
        )
        
        # Initialize portfolio with market microstructure
        portfolio = Portfolio(
            starting_balance=self.config.starting_balance,
            fee_per_contract=self.config.fee_per_contract,
            market_microstructure=market_microstructure
        )
        
        # Get unique hours to trade
        unique_hours = markets['hour_start'].unique()
        unique_hours = sorted(unique_hours)
        
        # Initialize explainability engine
        explainability = ExplainabilityEngine()
        
        results = {
            'strategy_name': strategy.name,
            'hours_traded': [],
            'initial_balance': self.config.starting_balance,
            'final_balance': None,
            'total_pnl': None,
            'portfolio': portfolio,
            'explainability': explainability
        }
        
        # Loop over each hour
        for hour_start in unique_hours:
            hour_result = self._simulate_hour(
                hour_start=hour_start,
                btc_prices=btc_prices,
                markets=markets,
                contract_prices=contract_prices,
                strategy=strategy,
                portfolio=portfolio,
                market_microstructure=market_microstructure
            )
            
            if hour_result:
                results['hours_traded'].append(hour_result)
        
        # Calculate final results
        results['final_balance'] = portfolio.cash
        results['total_pnl'] = portfolio.get_total_pnl()
        
        # Add market selection summary
        results['market_selection_summary'] = self.market_selector.get_selection_summary()
        
        return results
    
    def _simulate_hour(self,
                      hour_start: pd.Timestamp,
                      btc_prices: pd.DataFrame,
                      markets: pd.DataFrame,
                      contract_prices: pd.DataFrame,
                      strategy: Strategy,
                      portfolio: Portfolio,
                      market_microstructure: MarketMicrostructure) -> Dict:
        """
        Simulate trading for a single hour with market microstructure.
        
        Returns:
            Dictionary with hour results, or None if hour cannot be simulated
        """
        # Reset strategy and market microstructure for new hour
        strategy.reset()
        market_microstructure.reset_hour()
        
        # Select market for this hour
        market = self.market_selector.get_market_for_hour(
            hour_start=hour_start,
            btc_prices_df=btc_prices,
            markets_df=markets,
            contract_prices_df=contract_prices,
            use_intelligent_selection=True
        )
        
        if not market:
            return None
        
        hour_end = market['hour_end']
        strike_price = market['strike_price']
        
        # Get minute-by-minute data for this hour
        hour_mask = (btc_prices.index >= hour_start) & (btc_prices.index < hour_end)
        hour_btc_prices = btc_prices[hour_mask]
        
        if hour_btc_prices.empty:
            return None
        
        # Filter contract prices for this hour and strike
        contract_mask = (
            (contract_prices['timestamp'] >= hour_start) &
            (contract_prices['timestamp'] < hour_end) &
            (contract_prices['strike_price'] == strike_price)
        )
        hour_contract_prices = contract_prices[contract_mask]
        
        trades_executed = []
        btc_history = []  # Track BTC price history for dataset features
        pending_decisions = []  # Store decisions waiting for latency
        
        # Iterate minute-by-minute
        for timestamp in hour_btc_prices.index:
            # Get BTC price
            btc_price = hour_btc_prices.loc[timestamp, 'price']
            btc_history.append(btc_price)
            
            # Get contract prices (YES/NO)
            contract_data = hour_contract_prices[
                hour_contract_prices['timestamp'] == timestamp
            ]
            
            if contract_data.empty:
                continue
            
            yes_price = contract_data.iloc[0]['yes_price']
            no_price = contract_data.iloc[0]['no_price']
            
            # Collect dataset if enabled
            if self.dataset_factory is not None:
                self.dataset_factory.collect_minute_data(
                    timestamp=timestamp,
                    btc_price=btc_price,
                    yes_price=yes_price,
                    no_price=no_price,
                    strike_price=strike_price,
                    hour_start=hour_start,
                    btc_history=btc_history
                )
            
            # Feed data to strategy
            strategy.on_minute(
                timestamp=timestamp,
                btc_price=btc_price,
                yes_price=yes_price,
                no_price=no_price
            )
            
            # Get trade decision (this is the signal)
            action, quantity = strategy.decide_trade(portfolio)
            
            # Store decision with latency delay
            if action != TradeAction.HOLD and quantity:
                pending_decisions.append({
                    'decision_time': timestamp,
                    'action': action,
                    'quantity': quantity,
                    'yes_price': yes_price,
                    'no_price': no_price
                })
            
            # Execute trades that have passed the latency delay
            # Filter pending decisions into executable and remaining based on latency delay
            executable_decisions = []
            remaining_decisions = []
            
            for decision in pending_decisions:
                time_diff = (timestamp - decision['decision_time']).total_seconds() / 60
                
                if time_diff >= self.config.latency_minutes:
                    executable_decisions.append(decision)
                else:
                    remaining_decisions.append(decision)
            
            # Update pending list
            pending_decisions = remaining_decisions
            
            # Execute all ready trades
            for decision in executable_decisions:
                action = decision['action']
                quantity = decision['quantity']
                
                # Use current prices (after latency), not decision prices
                if action == TradeAction.BUY_YES:
                    success = portfolio.buy_yes(
                        quantity=quantity,
                        price=yes_price,  # Current price, not decision price
                        timestamp=timestamp,
                        strike_price=strike_price
                    )
                    if success:
                        # Get actual executed quantity from portfolio's trade history
                        last_trade = portfolio.trade_history[-1]
                        trades_executed.append({
                            'timestamp': timestamp,
                            'action': 'BUY_YES',
                            'quantity': last_trade['quantity'],
                            'price': last_trade['price'],
                            'decision_time': decision['decision_time']
                        })
                
                elif action == TradeAction.BUY_NO:
                    success = portfolio.buy_no(
                        quantity=quantity,
                        price=no_price,  # Current price, not decision price
                        timestamp=timestamp,
                        strike_price=strike_price
                    )
                    if success:
                        # Get actual executed quantity from portfolio's trade history
                        last_trade = portfolio.trade_history[-1]
                        trades_executed.append({
                            'timestamp': timestamp,
                            'action': 'BUY_NO',
                            'quantity': last_trade['quantity'],
                            'price': last_trade['price'],
                            'decision_time': decision['decision_time']
                        })
        
        # Get final BTC price at hour end
        if hour_end in btc_prices.index:
            final_btc_price = btc_prices.loc[hour_end, 'price']
        else:
            # Use last available price in the hour
            final_btc_price = hour_btc_prices.iloc[-1]['price']
        
        # Add labels to dataset if enabled
        if self.dataset_factory is not None:
            self.dataset_factory.add_labels(final_btc_price, strike_price, hour_start)
        
        # Resolve positions
        hour_pnl = portfolio.resolve_positions(
            final_btc_price=final_btc_price,
            resolution_time=hour_end
        )
        
        return {
            'hour_start': hour_start,
            'hour_end': hour_end,
            'strike_price': strike_price,
            'spot_price_start': market['btc_spot_price'],
            'final_btc_price': final_btc_price,
            'trades_executed': len(trades_executed),
            'hour_pnl': hour_pnl,
            'portfolio_value': portfolio.cash
        }
    
    def save_dataset(self, output_path: str) -> None:
        """
        Save collected dataset to CSV file.
        
        Args:
            output_path: Path to save the dataset CSV
            
        Raises:
            ValueError: If dataset was not collected (collect_dataset=False)
        """
        if self.dataset_factory is None:
            raise ValueError(
                "Dataset not collected. Run simulation with collect_dataset=True"
            )
        
        self.dataset_factory.save_csv(output_path)
    
    def get_dataset(self) -> Optional[pd.DataFrame]:
        """
        Get the collected dataset as a DataFrame.
        
        Returns:
            DataFrame with ML-ready features, or None if not collected
        """
        if self.dataset_factory is None:
            return None
        
        return self.dataset_factory.to_dataframe()
