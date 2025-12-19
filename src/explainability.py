"""
Explainability and diagnostics module for understanding strategy performance.

This module provides:
- Feature importance analysis
- Trade attribution (entry vs drift vs exit)
- Failure case clustering
- Diagnostic reports generation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict

# Constants for analysis thresholds
FAIR_VALUE_PRICE = 0.5  # Fair value for binary contracts
EXPENSIVE_ENTRY_THRESHOLD = 0.7  # Price above which entry is considered expensive
ABOVE_FAIR_VALUE_THRESHOLD = 0.5  # Threshold for above fair value entry

# BTC price movement thresholds for failure classification
LARGE_MISS_THRESHOLD = 500  # USD distance from strike for "large miss"
MEDIUM_MISS_THRESHOLD = 100  # USD distance from strike for "medium miss"

# Display constants
BAR_CHART_LENGTH = 30  # Character length for visual bar charts
EPSILON = 1e-6  # Small value for numerical stability


@dataclass
class TradeAttribution:
    """Attribution of PnL to different components."""
    entry_pnl: float  # PnL from entry price selection
    drift_pnl: float  # PnL from price movement during hold
    exit_pnl: float   # PnL from exit timing (for resolved positions, this is binary outcome)
    total_pnl: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'entry_pnl': self.entry_pnl,
            'drift_pnl': self.drift_pnl,
            'exit_pnl': self.exit_pnl,
            'total_pnl': self.total_pnl
        }


@dataclass
class FailureCase:
    """Represents a losing trade with context."""
    timestamp: pd.Timestamp
    trade_type: str
    entry_price: float
    strike_price: float
    pnl: float
    btc_price_at_entry: Optional[float] = None
    btc_price_at_exit: Optional[float] = None
    price_movement: Optional[float] = None
    failure_reason: Optional[str] = None


class ExplainabilityEngine:
    """
    Engine for analyzing and explaining strategy performance.
    
    Provides insights into:
    - Why trades won or lost
    - Which features contributed most to decisions
    - Common failure patterns
    """
    
    def __init__(self):
        """Initialize explainability engine."""
        self.feature_importance = {}
        self.trade_attributions = []
        self.failure_cases = []
        
    def calculate_feature_importance(self, 
                                     portfolio: 'Portfolio',
                                     strategy: 'Strategy') -> Dict[str, float]:
        """
        Calculate feature importance for trading decisions.
        
        Analyzes which features (price patterns, momentum, mean reversion)
        contributed most to profitable vs unprofitable trades.
        
        Args:
            portfolio: Portfolio with trade history
            strategy: Strategy used for trading
            
        Returns:
            Dictionary mapping feature names to importance scores (0-1)
        """
        if not portfolio.pnl_history:
            return {}
        
        pnl_df = pd.DataFrame(portfolio.pnl_history)
        
        # Calculate importance scores based on correlation with PnL
        importance = {}
        
        # Entry price quality (how good was the entry price)
        if len(pnl_df) > 0:
            # Lower entry price for YES or NO is better (more upside potential)
            winning_trades = pnl_df[pnl_df['pnl'] > 0]
            losing_trades = pnl_df[pnl_df['pnl'] < 0]
            
            if len(winning_trades) > 0 and len(losing_trades) > 0:
                win_avg_entry = winning_trades['entry_price'].mean()
                lose_avg_entry = losing_trades['entry_price'].mean()
                
                # Importance based on difference in entry prices
                importance['entry_price_quality'] = abs(win_avg_entry - lose_avg_entry)
            else:
                importance['entry_price_quality'] = 0.0
        
        # Market direction alignment (did we bet with or against the market?)
        if len(pnl_df) > 0 and 'final_btc_price' in pnl_df.columns and 'strike_price' in pnl_df.columns:
            # Calculate how often we correctly predicted direction
            pnl_df['btc_above_strike'] = pnl_df['final_btc_price'] >= pnl_df['strike_price']
            pnl_df['bet_yes'] = pnl_df['contract_type'] == 'YES'
            pnl_df['correct_direction'] = pnl_df['btc_above_strike'] == pnl_df['bet_yes']
            
            direction_accuracy = pnl_df['correct_direction'].mean()
            importance['market_direction_alignment'] = direction_accuracy
        else:
            importance['market_direction_alignment'] = 0.0
        
        # Trade timing (entry time during the hour)
        if len(pnl_df) > 0 and 'entry_time' in pnl_df.columns:
            # Analyze whether entry time is systematically related to PnL
            entry_times = pd.to_datetime(pnl_df['entry_time'], errors='coerce')
            valid_mask = entry_times.notna() & pnl_df['pnl'].notna()

            if valid_mask.sum() > 1 and entry_times[valid_mask].nunique() > 1:
                # Convert entry times to numeric (nanoseconds since epoch) for correlation
                entry_numeric = entry_times[valid_mask].view('int64')
                pnl_values = pnl_df.loc[valid_mask, 'pnl'].astype(float)

                # Correlation between entry time and PnL as a measure of timing importance
                corr_matrix = np.corrcoef(entry_numeric, pnl_values)
                corr = corr_matrix[0, 1] if corr_matrix.shape == (2, 2) else 0.0
                if np.isnan(corr):
                    corr = 0.0
                importance['trade_timing'] = float(abs(corr))
            else:
                importance['trade_timing'] = 0.0
        else:
            importance['trade_timing'] = 0.0
        
        # Position sizing discipline
        if len(pnl_df) > 0 and 'quantity' in pnl_df.columns:
            # Consistent position sizing is important
            quantity_variance = pnl_df['quantity'].std() / (pnl_df['quantity'].mean() + EPSILON)
            # Lower variance is better (more disciplined)
            importance['position_sizing_discipline'] = 1.0 / (1.0 + quantity_variance)
        else:
            importance['position_sizing_discipline'] = 0.0
        
        # Normalize importance scores to 0-1
        if importance:
            max_importance = max(importance.values())
            if max_importance > 0:
                importance = {k: v / max_importance for k, v in importance.items()}
        
        self.feature_importance = importance
        return importance
    
    def attribute_trade_pnl(self,
                           trade: Dict,
                           market_prices: Optional[List[Dict]] = None) -> TradeAttribution:
        """
        Attribute PnL to entry, drift, and exit components.
        
        For prediction markets:
        - Entry PnL: How good was the entry price (distance from 0.5)
        - Drift PnL: N/A for hourly markets (no mid-trade exits)
        - Exit PnL: Binary outcome (win $1 or lose to $0)
        
        Args:
            trade: Trade record from pnl_history
            market_prices: Optional list of price updates during trade
            
        Returns:
            TradeAttribution object
        """
        entry_price = trade['entry_price']
        payout = trade['payout']
        pnl = trade['pnl']
        
        # Entry quality: how much better than fair value
        # Avoid division by zero if entry_price equals FAIR_VALUE_PRICE
        if abs(entry_price - FAIR_VALUE_PRICE) < EPSILON:
            # Entry at fair value has neutral quality
            entry_quality = 0.0
        else:
            # Positive quality = cheaper than fair value (better entry), negative = more expensive
            entry_quality = (FAIR_VALUE_PRICE - entry_price) / FAIR_VALUE_PRICE  # Range: -1 to 1
        
        # Calculate entry PnL based on quality (independent of outcome)
        entry_pnl = entry_quality * abs(pnl)
        
        # Drift PnL: N/A for binary markets (no intra-trade price changes captured)
        drift_pnl = 0.0
        
        # Exit PnL: the binary outcome
        # This is the "luck" component - market resolution
        exit_pnl = pnl - entry_pnl
        
        return TradeAttribution(
            entry_pnl=entry_pnl,
            drift_pnl=drift_pnl,
            exit_pnl=exit_pnl,
            total_pnl=pnl
        )
    
    def analyze_trade_attributions(self, portfolio: 'Portfolio') -> Dict:
        """
        Analyze all trades and calculate aggregate attribution statistics.
        
        Args:
            portfolio: Portfolio with pnl_history
            
        Returns:
            Dictionary with attribution statistics
        """
        if not portfolio.pnl_history:
            return {
                'total_entry_pnl': 0.0,
                'total_drift_pnl': 0.0,
                'total_exit_pnl': 0.0,
                'avg_entry_pnl': 0.0,
                'avg_drift_pnl': 0.0,
                'avg_exit_pnl': 0.0,
                'num_trades': 0
            }
        
        self.trade_attributions = []
        
        for trade in portfolio.pnl_history:
            attribution = self.attribute_trade_pnl(trade)
            self.trade_attributions.append(attribution)
        
        # Calculate aggregate statistics
        total_entry = sum(a.entry_pnl for a in self.trade_attributions)
        total_drift = sum(a.drift_pnl for a in self.trade_attributions)
        total_exit = sum(a.exit_pnl for a in self.trade_attributions)
        num_trades = len(self.trade_attributions)
        
        return {
            'total_entry_pnl': total_entry,
            'total_drift_pnl': total_drift,
            'total_exit_pnl': total_exit,
            'avg_entry_pnl': total_entry / num_trades if num_trades > 0 else 0.0,
            'avg_drift_pnl': total_drift / num_trades if num_trades > 0 else 0.0,
            'avg_exit_pnl': total_exit / num_trades if num_trades > 0 else 0.0,
            'num_trades': num_trades
        }
    
    def identify_failure_cases(self, portfolio: 'Portfolio') -> List[FailureCase]:
        """
        Identify and cluster losing trades to understand failure patterns.
        
        Args:
            portfolio: Portfolio with pnl_history
            
        Returns:
            List of FailureCase objects
        """
        if not portfolio.pnl_history:
            return []
        
        self.failure_cases = []
        pnl_df = pd.DataFrame(portfolio.pnl_history)
        
        # Filter to losing trades
        losing_trades = pnl_df[pnl_df['pnl'] < 0]
        
        for _, trade in losing_trades.iterrows():
            # Determine failure reason
            failure_reason = self._classify_failure(trade)
            
            # Calculate price movement if data available
            price_movement = None
            if 'final_btc_price' in trade and 'strike_price' in trade:
                btc_at_exit = trade['final_btc_price']
                strike = trade['strike_price']
                price_movement = btc_at_exit - strike
            
            failure_case = FailureCase(
                timestamp=trade['timestamp'],
                trade_type=trade['contract_type'],
                entry_price=trade['entry_price'],
                strike_price=trade.get('strike_price', 0),
                pnl=trade['pnl'],
                btc_price_at_exit=trade.get('final_btc_price'),
                price_movement=price_movement,
                failure_reason=failure_reason
            )
            
            self.failure_cases.append(failure_case)
        
        return self.failure_cases
    
    def _classify_failure(self, trade: pd.Series) -> str:
        """
        Classify the reason for trade failure.
        
        Args:
            trade: Single trade record
            
        Returns:
            String describing failure reason
        """
        contract_type = trade['contract_type']
        entry_price = trade['entry_price']
        
        # Check if we have market outcome data
        if 'final_btc_price' in trade and 'strike_price' in trade:
            final_btc = trade['final_btc_price']
            strike = trade['strike_price']
            
            if contract_type == 'YES':
                # YES lost, meaning BTC < strike
                if final_btc < strike:
                    distance = abs(final_btc - strike)
                    if distance > LARGE_MISS_THRESHOLD:
                        return "Wrong direction (large miss)"
                    elif distance > MEDIUM_MISS_THRESHOLD:
                        return "Wrong direction (medium miss)"
                    else:
                        return "Wrong direction (close call)"
                else:
                    # Data inconsistency: YES lost but final_btc >= strike
                    return "Data inconsistency (YES lost but BTC >= strike)"
            else:  # NO
                # NO lost, meaning BTC >= strike
                if final_btc >= strike:
                    distance = abs(final_btc - strike)
                    if distance > LARGE_MISS_THRESHOLD:
                        return "Wrong direction (large miss)"
                    elif distance > MEDIUM_MISS_THRESHOLD:
                        return "Wrong direction (medium miss)"
                    else:
                        return "Wrong direction (close call)"
                else:
                    # Data inconsistency: NO lost but final_btc < strike
                    return "Data inconsistency (NO lost but BTC < strike)"
        
        # Price-based classification
        if entry_price > EXPENSIVE_ENTRY_THRESHOLD:
            return "Expensive entry (low reward/risk)"
        elif entry_price > ABOVE_FAIR_VALUE_THRESHOLD:
            return "Above fair value entry"
        else:
            return "Market moved against position"
    
    def cluster_failures(self) -> Dict[str, List[FailureCase]]:
        """
        Cluster failure cases by reason.
        
        Returns:
            Dictionary mapping failure reasons to lists of failure cases
        """
        clusters = defaultdict(list)
        
        for failure in self.failure_cases:
            clusters[failure.failure_reason].append(failure)
        
        return dict(clusters)
    
    def generate_hourly_report(self,
                              hour_result: Dict,
                              portfolio: 'Portfolio',
                              strategy: 'Strategy') -> str:
        """
        Generate a diagnostic report for a specific hour.
        
        Answers: "Why did we lose/win money this hour?"
        
        Args:
            hour_result: Results from simulating one hour
            portfolio: Portfolio state
            strategy: Strategy used
            
        Returns:
            String report
        """
        hour_start = hour_result['hour_start']
        hour_pnl = hour_result['hour_pnl']
        trades_executed = hour_result['trades_executed']
        
        report_lines = []
        report_lines.append(f"\n{'='*70}")
        report_lines.append(f"Diagnostic Report: Hour {hour_start}")
        report_lines.append(f"{'='*70}")
        report_lines.append(f"Strategy: {strategy.name}")
        report_lines.append(f"Hour PnL: ${hour_pnl:.2f}")
        report_lines.append(f"Trades Executed: {trades_executed}")
        report_lines.append(f"Strike Price: ${hour_result['strike_price']:.2f}")
        report_lines.append(f"BTC Start: ${hour_result['spot_price_start']:.2f}")
        report_lines.append(f"BTC End: ${hour_result['final_btc_price']:.2f}")
        report_lines.append(f"")
        
        # Overall outcome
        if hour_pnl > 0:
            report_lines.append(f"✓ PROFITABLE HOUR (+${hour_pnl:.2f})")
        elif hour_pnl < 0:
            report_lines.append(f"✗ LOSING HOUR (-${abs(hour_pnl):.2f})")
        else:
            report_lines.append(f"○ NO TRADES / BREAK EVEN")
        report_lines.append(f"")
        
        # Get trades for this hour
        # Trade timestamp is the resolution time (hour_end), so we need to match exactly
        hour_trades = [t for t in portfolio.pnl_history 
                      if t['timestamp'] == hour_result['hour_end']]
        
        if hour_trades:
            report_lines.append(f"Trade Analysis:")
            report_lines.append(f"-" * 70)
            
            for i, trade in enumerate(hour_trades, 1):
                attribution = self.attribute_trade_pnl(trade)
                
                report_lines.append(f"\nTrade #{i}:")
                report_lines.append(f"  Type: {trade['contract_type']}")
                report_lines.append(f"  Entry Price: ${trade['entry_price']:.3f}")
                report_lines.append(f"  Quantity: {trade['quantity']:.0f} contracts")
                report_lines.append(f"  Outcome: {'WIN' if trade['win'] else 'LOSS'}")
                report_lines.append(f"  PnL: ${trade['pnl']:.2f}")
                report_lines.append(f"  ")
                report_lines.append(f"  PnL Attribution:")
                report_lines.append(f"    Entry Quality: ${attribution.entry_pnl:+.2f}")
                report_lines.append(f"    Market Drift: ${attribution.drift_pnl:+.2f}")
                report_lines.append(f"    Exit/Outcome: ${attribution.exit_pnl:+.2f}")
                
                # Explain why trade won/lost
                if not trade['win']:
                    failure_reason = self._classify_failure(pd.Series(trade))
                    report_lines.append(f"  Failure Reason: {failure_reason}")
        else:
            report_lines.append(f"No trades executed this hour.")
        
        report_lines.append(f"\n{'='*70}\n")
        
        return "\n".join(report_lines)
    
    def generate_summary_report(self, 
                               portfolio: 'Portfolio',
                               strategy: 'Strategy',
                               results: Dict) -> str:
        """
        Generate overall summary report with key insights.
        
        Args:
            portfolio: Portfolio with full history
            strategy: Strategy used
            results: Full simulation results
            
        Returns:
            String report
        """
        # Calculate all analyses
        feature_importance = self.calculate_feature_importance(portfolio, strategy)
        attributions = self.analyze_trade_attributions(portfolio)
        failures = self.identify_failure_cases(portfolio)
        failure_clusters = self.cluster_failures()
        
        report_lines = []
        report_lines.append(f"\n{'='*70}")
        report_lines.append(f"EXPLAINABILITY REPORT: {strategy.name}")
        report_lines.append(f"{'='*70}\n")
        
        # Feature Importance Section
        report_lines.append(f"1. FEATURE IMPORTANCE")
        report_lines.append(f"   (What factors most influenced performance?)")
        report_lines.append(f"{'-'*70}")
        
        if feature_importance:
            sorted_features = sorted(feature_importance.items(), 
                                   key=lambda x: x[1], reverse=True)
            for feature, importance in sorted_features:
                bar_length = int(importance * BAR_CHART_LENGTH)
                bar = '█' * bar_length + '░' * (BAR_CHART_LENGTH - bar_length)
                report_lines.append(f"   {feature:30s} {bar} {importance:.2%}")
        else:
            report_lines.append(f"   No trades to analyze")
        
        # Trade Attribution Section
        report_lines.append(f"\n2. TRADE ATTRIBUTION")
        report_lines.append(f"   (Where did PnL come from?)")
        report_lines.append(f"{'-'*70}")
        
        if attributions['num_trades'] > 0:
            report_lines.append(f"   Entry Quality:    ${attributions['total_entry_pnl']:+8.2f} (avg: ${attributions['avg_entry_pnl']:+.2f}/trade)")
            report_lines.append(f"   Market Drift:     ${attributions['total_drift_pnl']:+8.2f} (avg: ${attributions['avg_drift_pnl']:+.2f}/trade)")
            report_lines.append(f"   Exit/Outcome:     ${attributions['total_exit_pnl']:+8.2f} (avg: ${attributions['avg_exit_pnl']:+.2f}/trade)")
            report_lines.append(f"   {'─'*70}")
            total_pnl = results['total_pnl']
            report_lines.append(f"   Total PnL:        ${total_pnl:+8.2f}")
        else:
            report_lines.append(f"   No trades to analyze")
        
        # Failure Analysis Section
        report_lines.append(f"\n3. FAILURE CASE ANALYSIS")
        report_lines.append(f"   (Why did we lose money?)")
        report_lines.append(f"{'-'*70}")
        
        if failure_clusters:
            report_lines.append(f"   Total losing trades: {len(failures)}")
            report_lines.append(f"")
            report_lines.append(f"   Failure breakdown:")
            
            sorted_clusters = sorted(failure_clusters.items(), 
                                    key=lambda x: len(x[1]), reverse=True)
            
            for reason, cases in sorted_clusters:
                count = len(cases)
                total_loss = sum(abs(c.pnl) for c in cases)
                avg_loss = total_loss / count if count > 0 else 0
                report_lines.append(f"   • {reason}")
                report_lines.append(f"     Count: {count}, Total Loss: ${total_loss:.2f}, Avg: ${avg_loss:.2f}")
        else:
            if attributions['num_trades'] > 0:
                report_lines.append(f"   ✓ No losing trades!")
            else:
                report_lines.append(f"   No trades to analyze")
        
        # Key Insights
        report_lines.append(f"\n4. KEY INSIGHTS")
        report_lines.append(f"{'-'*70}")
        
        insights = self._generate_insights(portfolio, feature_importance, 
                                           attributions, failure_clusters)
        for insight in insights:
            report_lines.append(f"   • {insight}")
        
        report_lines.append(f"\n{'='*70}\n")
        
        return "\n".join(report_lines)
    
    def _generate_insights(self,
                          portfolio: 'Portfolio',
                          feature_importance: Dict[str, float],
                          attributions: Dict,
                          failure_clusters: Dict) -> List[str]:
        """
        Generate key insights from the analysis.
        
        Returns:
            List of insight strings
        """
        insights = []
        
        # Feature importance insights
        if feature_importance:
            top_feature = max(feature_importance.items(), key=lambda x: x[1])
            insights.append(f"Most important factor: {top_feature[0]} ({top_feature[1]:.1%})")
        
        # Attribution insights
        if attributions['num_trades'] > 0:
            if abs(attributions['total_entry_pnl']) > abs(attributions['total_exit_pnl']):
                insights.append("Entry selection was more important than market outcomes")
            else:
                insights.append("Market outcomes dominated entry quality")
            
            if attributions['avg_entry_pnl'] < 0:
                insights.append("Entry prices were generally poor (above fair value)")
            elif attributions['avg_entry_pnl'] > 0:
                insights.append("Entry prices were generally good (below fair value)")
        
        # Failure insights
        if failure_clusters:
            most_common = max(failure_clusters.items(), key=lambda x: len(x[1]))
            insights.append(f"Most common failure: {most_common[0]} ({len(most_common[1])} cases)")
            
            # Check for expensive entries
            expensive_entries = failure_clusters.get("Expensive entry (low reward/risk)", [])
            if len(expensive_entries) > 2:
                insights.append("Strategy is entering too many expensive positions (>0.7 price)")
        
        if not insights:
            insights.append("Insufficient trade data for meaningful insights")
        
        return insights
