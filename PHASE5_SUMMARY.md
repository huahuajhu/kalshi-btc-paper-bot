# Phase 5: Counterfactual Testing - Implementation Summary

## Overview

This implementation adds comprehensive counterfactual testing capabilities to answer the question: **"What should have happened?"**

By comparing active trading strategies against simple baseline strategies, we can determine which strategies generate true **alpha** (excess returns above simple approaches).

## Baseline Strategies Implemented

### 1. Always Buy YES (`AlwaysYesStrategy`)
- **Behavior**: Buys YES contracts at the start of every hour
- **Purpose**: Tests if a bullish bias (always betting BTC will go up) is profitable
- **Use Case**: Baseline for comparing more sophisticated strategies

### 2. Always Buy NO (`AlwaysNoStrategy`)
- **Behavior**: Buys NO contracts at the start of every hour
- **Purpose**: Tests if a bearish bias (always betting BTC won't go up) is profitable
- **Use Case**: Counter-baseline to Always YES

### 3. Random Trading (`RandomStrategy`)
- **Behavior**: Randomly chooses YES, NO, or HOLD at each hour start
- **Purpose**: Statistical baseline representing random chance
- **Use Case**: Ensures strategies beat random selection
- **Parameters**: Uses seed=42 for reproducibility

### 4. BTC-Only Signal (`BtcOnlyStrategy`)
- **Behavior**: Trades based purely on BTC price momentum, ignoring Kalshi contract prices
- **Logic**:
  - If BTC rising → BUY YES
  - If BTC falling → BUY NO
  - Otherwise → HOLD
- **Purpose**: Isolates BTC signal effectiveness
- **Use Case**: Tests if BTC momentum alone predicts outcomes

## Visualization & Analysis

The implementation generates three comprehensive charts in the `output/` directory:

### 1. Alpha Comparison Chart (`alpha_comparison.png`)
A 9-panel visualization showing:
1. **Total PnL by Strategy** - Absolute profit/loss
2. **Return % by Strategy** - Percentage returns
3. **Alpha vs Baseline (PnL)** - Excess profit vs NoTrade
4. **Alpha vs Baseline (Return %)** - Excess return percentage
5. **Win Rate Comparison** - Percentage of winning trades
6. **Total Trades** - Trading activity
7. **Average Trade PnL** - Mean profit per trade
8. **Maximum Drawdown** - Risk measurement
9. **Calmar Ratio** - Risk-adjusted returns (Return % / Max Drawdown %)

### 2. Performance Table (`performance_table.png`)
Color-coded summary table with:
- Strategy name
- Total PnL ($)
- Return (%)
- Alpha PnL ($) - excess vs baseline
- Alpha (%) - excess return vs baseline
- Number of trades
- Win rate (%)
- Average trade PnL ($)
- Maximum drawdown (%)

**Color Coding**:
- 🟢 Green: Positive values (profitable)
- 🔴 Red: Negative values (losses)
- 🔵 Blue: Header

### 3. Equity Curves (`equity_curves.png`)
Line chart showing portfolio value evolution over time for all strategies, making it easy to:
- Compare strategy trajectories
- Identify consistent performers
- Spot high-variance strategies
- See drawdown periods

## Key Features

### Alpha Calculation
Alpha is calculated as the excess return over the baseline (NoTrade):
```
Alpha PnL = Strategy PnL - Baseline PnL
Alpha Return % = Strategy Return % - Baseline Return %
```

### Risk-Adjusted Metrics
The Calmar ratio provides risk-adjusted performance:
```
Calmar Ratio = Return % / Max Drawdown %
```
- Higher values indicate better risk-adjusted returns
- Accounts for both profitability and risk
- Handles edge cases (zero drawdown)

### Reproducibility
- Random strategy uses fixed seed (42) for consistent results
- All charts use same baseline for comparison
- Clear documentation of strategy logic

## Files Added/Modified

### New Files:
1. `src/strategies/always_yes.py` - Always YES baseline
2. `src/strategies/always_no.py` - Always NO baseline
3. `src/strategies/random_trade.py` - Random trading baseline
4. `src/strategies/btc_only.py` - BTC-only signal baseline
5. `src/visualizations.py` - Visualization and alpha analysis module

### Modified Files:
1. `main.py` - Added baseline strategies and visualization generation
2. `requirements.txt` - Added matplotlib>=3.7.0
3. `.gitignore` - Added output/ directory
4. `README.md` - Comprehensive documentation

## Example Output

```
============================================================
Strategy Comparison
============================================================
strategy_name  total_pnl  return_pct  final_balance  total_trades  wins  losses   win_rate
    AlwaysYes  397660.00   3976.6000      407660.00             3     3       0 100.000000
       Random  360600.00   3606.0000      370600.00             2     2       0 100.000000
      BtcOnly   99220.30    992.2030      109220.30             3     3       0 100.000000
      NoTrade       0.00      0.0000       10000.00             0     0       0   0.000000
     Momentum       0.00      0.0000       10000.00             0     0       0   0.000000
MeanReversion   -1819.55    -18.1955        8180.45             3     1       2  33.333333
     AlwaysNo   -2709.19    -27.0919        7290.81             3     0       3   0.000000

✓ Alpha comparison chart saved to: output/alpha_comparison.png
✓ Performance table saved to: output/performance_table.png
✓ Equity curves chart saved to: output/equity_curves.png
```

## Usage

Simply run the simulator:
```bash
python main.py
```

The simulator will:
1. Run all strategies (original + baselines)
2. Calculate performance metrics
3. Generate alpha comparison charts
4. Save visualizations to `output/` directory

## Insights from Counterfactual Testing

With these baselines, you can now answer:
- **Does my strategy beat doing nothing?** (vs NoTrade)
- **Does it beat simple directional bias?** (vs AlwaysYes/AlwaysNo)
- **Does it beat random chance?** (vs Random)
- **Is it better than pure BTC signals?** (vs BtcOnly)
- **How much alpha does it generate?** (excess vs baseline)
- **Is the alpha worth the risk?** (Calmar ratio)

## Technical Quality

- ✅ All strategies follow the base Strategy interface
- ✅ Comprehensive docstrings and type hints
- ✅ Clean separation of concerns (strategies, metrics, visualization)
- ✅ Proper error handling and edge cases
- ✅ No security vulnerabilities (CodeQL verified)
- ✅ Code review feedback addressed
- ✅ Output directory properly gitignored
- ✅ Matplotlib dependencies properly specified

## Next Steps

This foundation enables:
1. **Strategy optimization** - Compare variants against baselines
2. **Market regime analysis** - Test baselines in different market conditions
3. **Statistical testing** - Determine if alpha is statistically significant
4. **Portfolio construction** - Combine strategies that beat baselines
5. **Risk management** - Use Calmar ratios to size positions

---

**Implementation Status**: ✅ Complete and Tested
**Security Status**: ✅ No vulnerabilities detected
**Documentation**: ✅ Comprehensive README and code comments
