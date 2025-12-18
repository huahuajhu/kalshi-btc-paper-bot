"""Main simulator for paper trading."""

import pandas as pd
from typing import Dict
from .config import SimulationConfig
from .data_loader import DataLoader
from .market_selector import MarketSelector
from .contract_pricing import ContractPricer
from .portfolio import Portfolio
from .market_microstructure import MarketMicrostructure
from .strategies.base import Strategy, TradeAction


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
        
    def run(self, strategy: Strategy) -> Dict:
        """
        Run simulation with a given strategy.
        
        Args:
            strategy: Trading strategy to use
            
        Returns:
            Dictionary with simulation results
        """
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
        
        results = {
            'strategy_name': strategy.name,
            'hours_traded': [],
            'initial_balance': self.config.starting_balance,
            'final_balance': None,
            'total_pnl': None,
            'portfolio': portfolio
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
            markets_df=markets
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
        pending_decisions = []  # Store decisions waiting for latency
        
        # Iterate minute-by-minute
        for timestamp in hour_btc_prices.index:
            # Get BTC price
            btc_price = hour_btc_prices.loc[timestamp, 'price']
            
            # Get contract prices (YES/NO)
            contract_data = hour_contract_prices[
                hour_contract_prices['timestamp'] == timestamp
            ]
            
            if contract_data.empty:
                continue
            
            yes_price = contract_data.iloc[0]['yes_price']
            no_price = contract_data.iloc[0]['no_price']
            
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
