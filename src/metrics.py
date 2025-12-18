"""Metrics calculation for strategy performance."""

import pandas as pd
import numpy as np
from typing import Dict, List


class MetricsCalculator:
    """
    Compute metrics:
    - total PnL
    - win rate
    - average trade duration
    - max drawdown
    - strategy comparison table
    """
    
    @staticmethod
    def calculate_metrics(results: Dict) -> Dict:
        """
        Calculate performance metrics for a simulation result.
        
        Args:
            results: Results dictionary from simulator
            
        Returns:
            Dictionary of calculated metrics
        """
        portfolio = results['portfolio']
        
        metrics = {
            'strategy_name': results['strategy_name'],
            'total_pnl': results['total_pnl'],
            'final_balance': results['final_balance'],
            'return_pct': (results['total_pnl'] / results['initial_balance']) * 100,
            'num_hours': len(results['hours_traded']),
        }
        
        # Calculate trade-level metrics
        if portfolio.pnl_history:
            pnl_df = pd.DataFrame(portfolio.pnl_history)
            
            # Win rate
            wins = (pnl_df['pnl'] > 0).sum()
            total_trades = len(pnl_df)
            metrics['win_rate'] = (wins / total_trades * 100) if total_trades > 0 else 0
            metrics['total_trades'] = total_trades
            metrics['wins'] = wins
            metrics['losses'] = total_trades - wins
            
            # Average trade PnL
            metrics['avg_trade_pnl'] = pnl_df['pnl'].mean()
            metrics['avg_win'] = pnl_df[pnl_df['pnl'] > 0]['pnl'].mean() if wins > 0 else 0
            metrics['avg_loss'] = pnl_df[pnl_df['pnl'] < 0]['pnl'].mean() if (total_trades - wins) > 0 else 0
            
            # Calculate trade duration
            if portfolio.trade_history:
                trade_df = pd.DataFrame(portfolio.trade_history)

                # Derive average trade duration from entry and exit timestamps if available
                if 'entry_timestamp' in trade_df.columns and 'exit_timestamp' in trade_df.columns:
                    entry_times = pd.to_datetime(trade_df['entry_timestamp'])
                    exit_times = pd.to_datetime(trade_df['exit_timestamp'])
                    durations = (exit_times - entry_times).dt.total_seconds() / 60.0
                    metrics['avg_trade_duration_minutes'] = float(durations.mean()) if len(durations) > 0 else 0
                else:
                    # If we do not have both timestamps, we cannot compute a reliable duration
                    metrics['avg_trade_duration_minutes'] = 0
            else:
                metrics['avg_trade_duration_minutes'] = 0
        else:
            metrics['win_rate'] = 0
            metrics['total_trades'] = 0
            metrics['wins'] = 0
            metrics['losses'] = 0
            metrics['avg_trade_pnl'] = 0
            metrics['avg_win'] = 0
            metrics['avg_loss'] = 0
            metrics['avg_trade_duration_minutes'] = 0
        
        # Calculate max drawdown
        metrics['max_drawdown'] = MetricsCalculator._calculate_max_drawdown(results)
        
        return metrics
    
    @staticmethod
    def _calculate_max_drawdown(results: Dict) -> float:
        """
        Calculate maximum drawdown.
        
        Args:
            results: Results dictionary from simulator
            
        Returns:
            Maximum drawdown as a percentage
        """
        hours = results['hours_traded']
        if not hours:
            return 0.0
        
        # Build equity curve
        equity = [results['initial_balance']]
        for hour in hours:
            equity.append(hour['portfolio_value'])
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(equity)
        
        # Calculate drawdown at each point
        drawdown = (equity - running_max) / running_max * 100
        
        # Return maximum drawdown (most negative value)
        return abs(min(drawdown))
    
    @staticmethod
    def create_comparison_table(all_results: List[Dict]) -> pd.DataFrame:
        """
        Create a comparison table for multiple strategies.
        
        Args:
            all_results: List of results dictionaries from multiple strategies
            
        Returns:
            DataFrame with strategy comparison
        """
        metrics_list = []
        
        for result in all_results:
            metrics = MetricsCalculator.calculate_metrics(result)
            metrics_list.append(metrics)
        
        df = pd.DataFrame(metrics_list)
        
        # Select and order columns
        columns = [
            'strategy_name',
            'total_pnl',
            'return_pct',
            'final_balance',
            'total_trades',
            'wins',
            'losses',
            'win_rate',
            'avg_trade_pnl',
            'max_drawdown',
            'num_hours'
        ]
        
        # Only include columns that exist
        columns = [col for col in columns if col in df.columns]
        
        return df[columns].sort_values('total_pnl', ascending=False)
    
    @staticmethod
    def print_metrics(metrics: Dict) -> None:
        """Print metrics in a readable format."""
        print(f"\n{'='*60}")
        print(f"Strategy: {metrics['strategy_name']}")
        print(f"{'='*60}")
        print(f"Total PnL:          ${metrics['total_pnl']:.2f}")
        print(f"Return:             {metrics['return_pct']:.2f}%")
        print(f"Final Balance:      ${metrics['final_balance']:.2f}")
        print(f"Total Trades:       {metrics['total_trades']}")
        print(f"Win Rate:           {metrics['win_rate']:.2f}%")
        print(f"Wins/Losses:        {metrics['wins']}/{metrics['losses']}")
        print(f"Avg Trade PnL:      ${metrics['avg_trade_pnl']:.2f}")
        print(f"Max Drawdown:       {metrics['max_drawdown']:.2f}%")
        print(f"Hours Traded:       {metrics['num_hours']}")
        print(f"{'='*60}\n")
