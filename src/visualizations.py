"""Visualization module for strategy comparison and alpha analysis."""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict
from pathlib import Path


class StrategyVisualizer:
    """
    Create visualization charts for comparing strategies and analyzing alpha.
    """
    
    @staticmethod
    def create_alpha_comparison_charts(all_results: List[Dict], 
                                       baseline_name: str = "NoTrade",
                                       output_dir: str = "output") -> None:
        """
        Create comprehensive alpha comparison charts.
        
        Args:
            all_results: List of results dictionaries from multiple strategies
            baseline_name: Name of the baseline strategy for alpha calculation
            output_dir: Directory to save charts
        """
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Calculate metrics for all strategies
        metrics_list = []
        for result in all_results:
            from src.metrics import MetricsCalculator
            metrics = MetricsCalculator.calculate_metrics(result)
            metrics_list.append(metrics)
        
        df = pd.DataFrame(metrics_list)
        
        # Find baseline performance
        baseline = df[df['strategy_name'] == baseline_name]
        if baseline.empty:
            baseline_pnl = 0.0
            baseline_return = 0.0
        else:
            baseline_pnl = baseline.iloc[0]['total_pnl']
            baseline_return = baseline.iloc[0]['return_pct']
        
        # Calculate alpha (excess return over baseline)
        df['alpha_pnl'] = df['total_pnl'] - baseline_pnl
        df['alpha_return'] = df['return_pct'] - baseline_return
        
        # Create figure with multiple subplots
        fig = plt.figure(figsize=(16, 12))
        
        # 1. Total PnL Comparison
        ax1 = plt.subplot(3, 3, 1)
        strategies = df['strategy_name']
        pnl = df['total_pnl']
        colors = ['green' if x >= 0 else 'red' for x in pnl]
        ax1.barh(strategies, pnl, color=colors, alpha=0.7)
        ax1.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        ax1.set_xlabel('Total PnL ($)')
        ax1.set_title('Total PnL by Strategy')
        ax1.grid(True, alpha=0.3)
        
        # 2. Return % Comparison
        ax2 = plt.subplot(3, 3, 2)
        returns = df['return_pct']
        colors = ['green' if x >= 0 else 'red' for x in returns]
        ax2.barh(strategies, returns, color=colors, alpha=0.7)
        ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        ax2.set_xlabel('Return (%)')
        ax2.set_title('Return % by Strategy')
        ax2.grid(True, alpha=0.3)
        
        # 3. Alpha vs Baseline (PnL)
        ax3 = plt.subplot(3, 3, 3)
        alpha_pnl = df['alpha_pnl']
        colors = ['green' if x >= 0 else 'red' for x in alpha_pnl]
        ax3.barh(strategies, alpha_pnl, color=colors, alpha=0.7)
        ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        ax3.set_xlabel('Alpha ($)')
        ax3.set_title(f'Alpha vs {baseline_name} (PnL)')
        ax3.grid(True, alpha=0.3)
        
        # 4. Alpha vs Baseline (Return %)
        ax4 = plt.subplot(3, 3, 4)
        alpha_return = df['alpha_return']
        colors = ['green' if x >= 0 else 'red' for x in alpha_return]
        ax4.barh(strategies, alpha_return, color=colors, alpha=0.7)
        ax4.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        ax4.set_xlabel('Alpha (%)')
        ax4.set_title(f'Alpha vs {baseline_name} (Return %)')
        ax4.grid(True, alpha=0.3)
        
        # 5. Win Rate Comparison
        ax5 = plt.subplot(3, 3, 5)
        win_rate = df['win_rate']
        ax5.barh(strategies, win_rate, color='steelblue', alpha=0.7)
        ax5.set_xlabel('Win Rate (%)')
        ax5.set_title('Win Rate by Strategy')
        ax5.grid(True, alpha=0.3)
        
        # 6. Total Trades
        ax6 = plt.subplot(3, 3, 6)
        trades = df['total_trades']
        ax6.barh(strategies, trades, color='orange', alpha=0.7)
        ax6.set_xlabel('Number of Trades')
        ax6.set_title('Total Trades by Strategy')
        ax6.grid(True, alpha=0.3)
        
        # 7. Average Trade PnL
        ax7 = plt.subplot(3, 3, 7)
        avg_pnl = df['avg_trade_pnl']
        colors = ['green' if x >= 0 else 'red' for x in avg_pnl]
        ax7.barh(strategies, avg_pnl, color=colors, alpha=0.7)
        ax7.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        ax7.set_xlabel('Avg Trade PnL ($)')
        ax7.set_title('Average Trade PnL')
        ax7.grid(True, alpha=0.3)
        
        # 8. Max Drawdown
        ax8 = plt.subplot(3, 3, 8)
        drawdown = df['max_drawdown']
        ax8.barh(strategies, drawdown, color='darkred', alpha=0.7)
        ax8.set_xlabel('Max Drawdown (%)')
        ax8.set_title('Maximum Drawdown by Strategy')
        ax8.grid(True, alpha=0.3)
        
        # 9. Risk-Adjusted Return (Return / Max Drawdown)
        ax9 = plt.subplot(3, 3, 9)
        # Avoid division by zero
        risk_adjusted = df.apply(
            lambda row: row['return_pct'] / row['max_drawdown'] if row['max_drawdown'] > 0 else 0,
            axis=1
        )
        colors = ['green' if x >= 0 else 'red' for x in risk_adjusted]
        ax9.barh(strategies, risk_adjusted, color=colors, alpha=0.7)
        ax9.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        ax9.set_xlabel('Risk-Adjusted Return')
        ax9.set_title('Risk-Adjusted Return\n(Return % / Max Drawdown %)')
        ax9.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save the figure
        output_path = Path(output_dir) / 'alpha_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\n✓ Alpha comparison chart saved to: {output_path}")
        
        plt.close()
        
        # Create a second chart: Strategy Performance Summary Table
        StrategyVisualizer._create_performance_table(df, output_dir)
        
        # Create a third chart: Equity Curves
        StrategyVisualizer._create_equity_curves(all_results, output_dir)
    
    @staticmethod
    def _create_performance_table(df: pd.DataFrame, output_dir: str) -> None:
        """Create a visual table of strategy performance metrics."""
        fig, ax = plt.subplots(figsize=(14, len(df) * 0.6 + 2))
        ax.axis('tight')
        ax.axis('off')
        
        # Select key columns
        table_df = df[[
            'strategy_name', 'total_pnl', 'return_pct', 'alpha_pnl', 'alpha_return',
            'total_trades', 'win_rate', 'avg_trade_pnl', 'max_drawdown'
        ]].copy()
        
        # Round numeric columns
        table_df['total_pnl'] = table_df['total_pnl'].round(2)
        table_df['return_pct'] = table_df['return_pct'].round(2)
        table_df['alpha_pnl'] = table_df['alpha_pnl'].round(2)
        table_df['alpha_return'] = table_df['alpha_return'].round(2)
        table_df['win_rate'] = table_df['win_rate'].round(2)
        table_df['avg_trade_pnl'] = table_df['avg_trade_pnl'].round(2)
        table_df['max_drawdown'] = table_df['max_drawdown'].round(2)
        
        # Rename columns for display
        table_df.columns = [
            'Strategy', 'PnL ($)', 'Return (%)', 'Alpha PnL ($)', 'Alpha (%)',
            'Trades', 'Win Rate (%)', 'Avg Trade ($)', 'Max DD (%)'
        ]
        
        # Sort by total PnL
        table_df = table_df.sort_values('PnL ($)', ascending=False)
        
        # Create table
        table = ax.table(cellText=table_df.values,
                        colLabels=table_df.columns,
                        cellLoc='center',
                        loc='center',
                        colWidths=[0.12] * len(table_df.columns))
        
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        
        # Color code cells
        for i in range(len(table_df)):
            for j in range(len(table_df.columns)):
                cell = table[(i + 1, j)]
                if j in [1, 2, 3, 4, 7]:  # PnL, Return, Alpha columns, Avg Trade
                    value = table_df.iloc[i, j]
                    if value > 0:
                        cell.set_facecolor('#90EE90')  # Light green
                    elif value < 0:
                        cell.set_facecolor('#FFB6C1')  # Light red
        
        # Style header
        for j in range(len(table_df.columns)):
            cell = table[(0, j)]
            cell.set_facecolor('#4472C4')
            cell.set_text_props(weight='bold', color='white')
        
        plt.title('Strategy Performance Summary', fontsize=14, fontweight='bold', pad=20)
        
        output_path = Path(output_dir) / 'performance_table.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ Performance table saved to: {output_path}")
        plt.close()
    
    @staticmethod
    def _create_equity_curves(all_results: List[Dict], output_dir: str) -> None:
        """Create equity curve chart showing portfolio value over time."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for result in all_results:
            strategy_name = result['strategy_name']
            initial_balance = result['initial_balance']
            hours = result['hours_traded']
            
            if not hours:
                continue
            
            # Build equity curve
            equity = [initial_balance]
            hour_labels = [0]
            
            for i, hour in enumerate(hours, 1):
                equity.append(hour['portfolio_value'])
                hour_labels.append(i)
            
            # Plot
            ax.plot(hour_labels, equity, marker='o', label=strategy_name, linewidth=2, markersize=4)
        
        ax.set_xlabel('Trading Hour')
        ax.set_ylabel('Portfolio Value ($)')
        ax.set_title('Equity Curves: Portfolio Value Over Time')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=all_results[0]['initial_balance'], 
                   color='black', linestyle='--', linewidth=1, alpha=0.5, label='Starting Balance')
        
        output_path = Path(output_dir) / 'equity_curves.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ Equity curves chart saved to: {output_path}")
        plt.close()
