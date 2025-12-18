# Kalshi BTC Paper Trading Simulator

Simulate paper trading on Kalshi hourly BTC price markets with different trading strategies.

## Overview

This simulator allows you to backtest trading strategies on Kalshi's hourly BTC price prediction markets. Each hour represents a separate market with multiple strike prices at $250 intervals. The simulator executes minute-by-minute trades and calculates PnL at market resolution.

## Features

- **Hourly Markets**: Each hour (e.g., 1pm-2pm) is a separate market
- **Strike Buckets**: Markets are available at $250 price intervals
- **Intelligent Market Selection** (Phase 2): Smart strike selection based on:
  - Expected volatility
  - Market liquidity (volume proxy)
  - YES/NO spread tightness
  - Price reaction to BTC movements
- **Market Selection Logging**: Detailed CSV log with selection rationale and metrics
- **Minute-by-Minute Trading**: Simulates YES/NO price evolution every minute
- **Multiple Strategies**: Compare different trading approaches
- **Performance Metrics**: Track PnL, win rate, drawdown, and more
- **🆕 Phase 4: Market Microstructure Modeling**:
  - **Bid-ask spreads**: Realistic cost of crossing the spread
  - **Slippage model**: Price impact scales with order size
  - **Limited liquidity**: Max tradeable volume per minute
  - **Latency delays**: 1-2 minute reaction delay between signal and execution

## Market Mechanics

1. **At Hour Start (e.g., 13:00)**:
   - BTC spot price is sampled
   - Intelligent market selector analyzes all available strikes:
     - Calculates spread (YES + NO price deviation from 1.00)
     - Estimates volume proxy (sum of price changes)
     - Measures price reaction (correlation with BTC price movements)
     - Filters out low-liquidity markets
     - Scores and selects the best market based on weighted criteria
   - Fallback to closest strike if no liquid markets found
   - Market is active for 60 minutes

2. **During the Hour (13:00-14:00)**:
   - YES and NO contract prices update minute-by-minute
   - Prices satisfy: `YES + NO ≈ 1.00`
   - Strategies analyze prices and execute trades

3. **At Hour End (14:00)**:
   - Final BTC price determines market outcome
   - If BTC ≥ strike: YES wins ($1.00), NO loses ($0.00)
   - If BTC < strike: NO wins ($1.00), YES loses ($0.00)
   - PnL is calculated for all positions

## Market Selection Intelligence

The simulator implements Phase 2 market selection intelligence to pick the *right market* based on:

### Selection Criteria (Priority Order)

1. **Liquidity Filter**: Exclude markets with low trading activity
   - Volume proxy < threshold (default: 0.01)

2. **Market Quality Scoring** (for liquid markets):
   - **Spread Score (40% weight)**: Lower spread = better
     - Measures tightness of YES/NO prices
   - **Volume Score (30% weight)**: Higher volume = better
     - Proxy: sum of YES/NO price changes
   - **Reaction Score (30% weight)**: Higher correlation = better
     - Correlation between BTC price changes and contract price changes

3. **Volatility Consideration**:
   - Estimates recent BTC volatility (24h lookback)
   - Logged for analysis in selection metrics (not currently used in strike selection scoring)

### Output Files

- **`data/market_selection_log.csv`**: Detailed log of every selection decision
  - Columns: hour_start, btc_spot_price, selected_strike, selection_method, avg_spread, avg_volume_proxy, price_reaction_score, volatility_estimate, num_strikes_considered, reason
  
- **Market Selection Summary**: Printed after each strategy simulation
  - Total selections, intelligent vs fallback selections
  - Average spread, volume, reaction, and volatility metrics

## Installation

```bash
# Clone the repository
git clone https://github.com/huahuajhu/kalshi-btc-paper-bot.git
cd kalshi-btc-paper-bot

# Install dependencies
pip install -r requirements.txt
```

## Usage

Run the simulator with default settings:

```bash
python main.py
```

The simulator will:
1. Load BTC prices, markets, and contract prices from `data/`
2. Run simulations for all strategies
3. Print performance metrics and comparison table
4. Generate `data/market_selection_log.csv` with detailed selection decisions

### Example Output

```
Market Selection Summary:
 total_selections  intelligent_selections  fallback_selections  avg_spread  avg_volume_proxy  avg_price_reaction  avg_volatility
                9                       9                    0         0.0         10.786667            0.458366        0.000546

Market selection log saved to: data/market_selection_log.csv
```

## Daily Data Collection

Collect today's BTC minute prices and Kalshi BTC hourly market snapshots:

```bash
# Optional: set your Kalshi API token for market data
export KALSHI_API_TOKEN="your_token_here"

python -m src.data_pipeline
```

Options:
- `--date YYYY-MM-DD` to backfill a specific UTC date
- `--skip-btc` or `--skip-kalshi` to disable one side of the pipeline
- `--btc-file`, `--markets-file`, `--contracts-file` to override output paths

Output files (appended and de-duplicated):
- `data/btc_prices_minute.csv` (`timestamp,price`)
- `data/kalshi_markets.csv` (`hour_start,strike_price`)
- `data/kalshi_contract_prices.csv` (`timestamp,strike_price,yes_price,no_price`)

## Project Structure

```
kalshi-btc-paper-bot/
│
├── data/                          # Market data
│   ├── btc_prices_minute.csv     # Minute-level BTC prices
│   ├── kalshi_markets.csv        # Hourly markets with strikes
│   └── kalshi_contract_prices.csv # YES/NO price evolution
│
├── src/                           # Core modules
│   ├── config.py                 # Configuration settings
│   ├── data_loader.py            # Data loading with validation
│   ├── market_selector.py        # Market selection logic
│   ├── contract_pricing.py       # YES/NO price simulation
│   ├── portfolio.py              # Position & PnL tracking
│   ├── simulator.py              # Main simulation engine
│   ├── metrics.py                # Performance metrics
│   ├── visualizations.py         # Alpha comparison charts
│   └── strategies/               # Trading strategies
│       ├── base.py              # Abstract strategy class
│       ├── momentum.py          # Momentum strategy
│       ├── mean_reversion.py   # Mean reversion strategy
│       ├── no_trade.py         # Baseline (no trades)
│       ├── always_yes.py       # Always buy YES baseline
│       ├── always_no.py        # Always buy NO baseline
│       ├── random_trade.py     # Random trading baseline
│       └── btc_only.py         # BTC-only signal baseline
│
├── notebooks/                     # Analysis notebooks
│   └── analysis.ipynb            # Performance analysis
│
├── output/                        # Generated visualizations
│   ├── alpha_comparison.png     # Multi-panel comparison
│   ├── performance_table.png    # Metrics summary table
│   └── equity_curves.png        # Portfolio value over time
│
├── main.py                        # Entry point
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Strategies

### 1. No Trade (Baseline)
- **Description**: Never trades, always holds cash
- **Purpose**: Baseline for comparison
- **Expected PnL**: $0

### 2. Momentum
- **Description**: Buys based on consecutive price increases
- **Rules**:
  - If YES price increased for N consecutive minutes → BUY YES
  - If NO price increased for N consecutive minutes → BUY NO
  - Otherwise → HOLD
- **Parameters**: 
  - `lookback_minutes`: Number of consecutive minutes to check (default: 3)
  - `max_position_pct`: Max % of portfolio per trade (default: 10%)

### 3. Mean Reversion
- **Description**: Trades against price extremes
- **Rules**:
  - If YES price > rolling mean + threshold → BUY NO
  - If NO price > rolling mean + threshold → BUY YES
  - Otherwise → HOLD
- **Parameters**:
  - `window_minutes`: Rolling window size (default: 10)
  - `threshold`: Deviation threshold (default: 0.05)
  - `max_position_pct`: Max % of portfolio per trade (default: 10%)

## Phase 5: Counterfactual Testing Baselines

These baseline strategies help answer "What should have happened?" by providing simple reference points for comparison.

### 4. Always Buy YES
- **Description**: Always buys YES contracts at the start of each hour
- **Purpose**: Baseline for bullish bias testing
- **Use Case**: Tests if simply betting BTC will go up is profitable

### 5. Always Buy NO
- **Description**: Always buys NO contracts at the start of each hour
- **Purpose**: Baseline for bearish bias testing
- **Use Case**: Tests if simply betting BTC won't go up is profitable

### 6. Random Trading
- **Description**: Randomly chooses to buy YES, NO, or hold at the start of each hour
- **Purpose**: Statistical baseline for random behavior
- **Use Case**: Ensures strategies beat random chance
- **Parameters**:
  - `seed`: Random seed for reproducibility (default: 42)

### 7. BTC-Only Signal
- **Description**: Trades based purely on BTC price movement, ignoring Kalshi prices
- **Rules**:
  - If BTC price rising for N minutes → BUY YES
  - If BTC price falling for N minutes → BUY NO
  - Otherwise → HOLD
- **Purpose**: Tests if BTC momentum alone is predictive
- **Use Case**: Isolates BTC signal from Kalshi pricing
- **Parameters**:
  - `lookback_minutes`: Number of minutes to check BTC trend (default: 3)

## Visualization & Alpha Analysis

The simulator now generates comprehensive alpha comparison charts in the `output/` directory:

1. **alpha_comparison.png** - 9-panel comparison showing:
   - Total PnL by strategy
   - Return % by strategy
   - Alpha vs baseline (PnL and Return %)
   - Win rate comparison
   - Total trades
   - Average trade PnL
   - Maximum drawdown
   - Risk-adjusted returns

2. **performance_table.png** - Color-coded performance summary table with all key metrics

3. **equity_curves.png** - Portfolio value over time for all strategies

These visualizations help identify which strategies generate **alpha** (excess returns) compared to simple baselines.
### 4. Opening Auction
- **Description**: Trade during the first 5-10 minutes of each hour
- **Rules**:
  - Only trade within opening window (first 5-10 minutes)
  - Buy YES if YES price is rising in the opening
  - Buy NO if NO price is rising in the opening
  - Hold position until resolution
- **Parameters**:
  - `opening_window_minutes`: Opening window duration (default: 10)
  - `min_price_increase`: Minimum price increase to trigger (default: 0.02)
  - `max_position_pct`: Max % of portfolio per trade (default: 10%)

### 5. Trend Continuation
- **Description**: Trade after momentum confirmation
- **Rules**:
  - Wait for clear trend to establish (price moving in one direction)
  - Confirm momentum with trend strength calculation
  - Enter in direction of confirmed trend
  - Only take one position per hour
- **Parameters**:
  - `confirmation_minutes`: Minutes to observe before confirming (default: 15)
  - `min_trend_strength`: Minimum trend strength to confirm (default: 0.05)
  - `max_position_pct`: Max % of portfolio per trade (default: 10%)

### 6. Volatility Compression
- **Description**: Fade breakouts after stagnation
- **Rules**:
  - Detect periods of low volatility (price compression)
  - When price breaks out after compression, fade the move
  - Assumption: Breakouts after stagnation often reverse
- **Parameters**:
  - `compression_window`: Minutes to check for compression (default: 20)
  - `compression_threshold`: Max range for compression (default: 0.02)
  - `breakout_threshold`: Min move to consider breakout (default: 0.03)
  - `max_position_pct`: Max % of portfolio per trade (default: 10%)

### 7. No-Trade Filter
- **Description**: Skip low BTC movement or wide spreads
- **Rules**:
  - Skip hours with low BTC volatility
  - Skip when YES/NO spreads are too wide (poor liquidity)
  - Uses simple momentum when conditions are favorable
- **Parameters**:
  - `min_btc_volatility`: Minimum BTC price range required (default: $50)
  - `max_spread`: Maximum acceptable YES+NO spread (default: 0.10)
  - `lookback_minutes`: Minutes to check volatility (default: 30)
  - `max_position_pct`: Max % of portfolio per trade (default: 10%)

## Configuration

Edit `src/config.py` or pass parameters to `SimulationConfig`:

```python
config = SimulationConfig(
    # Trading parameters
    starting_balance=10000.0,       # Starting capital
    max_position_pct=0.1,           # Max 10% per trade
    fee_per_contract=0.0,           # Trading fees
    
    # Market parameters
    btc_price_interval=250,         # Strike interval ($250)
    market_duration_minutes=60,     # 1 hour markets
    min_trade_price=0.01,           # Min contract price
    max_trade_price=0.99,           # Max contract price
    
    # Market microstructure (Phase 4)
    bid_ask_spread=0.02,            # Bid-ask spread ($0.02)
    slippage_per_100_contracts=0.01,  # Slippage per 100 contracts
    max_liquidity_per_minute=500.0,   # Max contracts per minute
    latency_minutes=1,              # Reaction delay (1-2 min)
)
```

## Data Format

### BTC Prices (`btc_prices_minute.csv`)
```csv
timestamp,price
2025-01-01 13:00:00,86510
2025-01-01 13:01:00,86540
...
```

### Markets (`kalshi_markets.csv`)
```csv
hour_start,strike_price
2025-01-01 13:00:00,86250
2025-01-01 13:00:00,86500
2025-01-01 13:00:00,86750
...
```

### Contract Prices (`kalshi_contract_prices.csv`)
```csv
timestamp,strike_price,yes_price,no_price
2025-01-01 13:00:00,86500,0.52,0.48
2025-01-01 13:01:00,86500,0.55,0.45
...
```

**Important**: YES + NO must always equal ≈ 1.00

## Metrics

The simulator calculates:

- **Total PnL**: Total profit/loss across all trades
- **Return %**: Percentage return on initial capital
- **Win Rate**: Percentage of profitable trades
- **Avg Trade PnL**: Average profit/loss per trade
- **Max Drawdown**: Maximum peak-to-trough decline
- **Total Trades**: Number of trades executed
- **Hour-by-Hour PnL**: Breakdown of performance by trading hour
- **Strategy Leaderboard**: Ranked comparison of all strategies

## Example Output

```
====================================================================================================
STRATEGY LEADERBOARD
====================================================================================================
 rank         strategy_name total_pnl return_pct final_balance  total_trades  wins  losses win_rate avg_trade_pnl max_drawdown  num_hours
    1        OpeningAuction   $979.62      9.80%     $10979.62             3     3       0  100.00%       $326.54        0.00%          3
    2 VolatilityCompression    $98.82      0.99%     $10098.82             1     1       0  100.00%        $98.82        0.00%          3
    3     TrendContinuation    $30.33      0.30%     $10030.33             3     3       0  100.00%        $10.11        0.00%          3
    4         NoTradeFilter    $30.33      0.30%     $10030.33             3     3       0  100.00%        $10.11        0.00%          3
    5               NoTrade     $0.00      0.00%     $10000.00             0     0       0    0.00%         $0.00        0.00%          3
    6              Momentum     $0.00      0.00%     $10000.00             0     0       0    0.00%         $0.00        0.00%          3
    7         MeanReversion $-1819.55    -18.20%      $8180.45             3     1       2   33.33%      $-606.52       19.00%          3
====================================================================================================

Showing hourly breakdown for top strategy: OpeningAuction

================================================================================
Hour-by-Hour PnL Breakdown - OpeningAuction
================================================================================
      hour_start            hour_end  strike_price  trades     pnl portfolio_value cumulative_pnl
2025-01-01 13:00 2025-01-01 14:00:00         86500       1  $10.10       $10010.10         $10.10
2025-01-01 14:00 2025-01-01 15:00:00         86750       1 $924.00       $10934.10        $934.10
2025-01-01 15:00 2025-01-01 16:00:00         87250       1  $45.52       $10979.62        $979.62
================================================================================
```

## Development

### Adding a New Strategy

1. Create a new file in `src/strategies/`
2. Inherit from `Strategy` base class
3. Implement `on_minute()` and `decide_trade()` methods
4. Add to strategy list in `main.py`

Example:

```python
from src.strategies.base import Strategy, TradeAction

class MyStrategy(Strategy):
    def __init__(self):
        super().__init__(name="MyStrategy")
    
    def on_minute(self, timestamp, btc_price, yes_price, no_price):
        self.history.append({
            'timestamp': timestamp,
            'btc_price': btc_price,
            'yes_price': yes_price,
            'no_price': no_price
        })
    
    def decide_trade(self, portfolio):
        # Your trading logic here
        return TradeAction.HOLD, None
```

## Market Microstructure (Phase 4)

The simulator now includes realistic market microstructure modeling to improve realism. These features help develop strategies that work in actual trading conditions, not just idealized backtests.

### Why Market Microstructure Matters

📌 **Kalshi contracts don't move like spot BTC.** Real markets have:

- **Bid-ask spreads**: You can't buy and sell at the same price
- **Slippage**: Large orders move prices against you
- **Liquidity limits**: You can't trade unlimited size instantly
- **Latency**: Real-world delays between signal and execution

### Features

#### 1. Bid-Ask Spreads
- Buyers pay the **ask price** (mid + half spread)
- Sellers receive the **bid price** (mid - half spread)
- Default: $0.02 spread
- Example: Mid-price $0.50 → Buy at $0.51, Sell at $0.49

#### 2. Slippage Model
- Larger orders cause more price impact
- Scales linearly with order size
- Default: $0.01 per 100 contracts
- Example: 500 contracts → $0.05 slippage

#### 3. Liquidity Limits
- Maximum contracts tradeable per minute
- Shared pool across all trades in that minute
- Partial fills when liquidity is exhausted
- Default: 500 contracts per minute

#### 4. Latency Delays
- Simulates delay between signal and execution
- Trades execute at prices available after delay
- Models processing time, network latency, platform delays
- Default: 1 minute delay
- Impact: Trading on stale signals reduces profitability

### Impact on Trading

These features significantly affect strategy performance:

1. **Transaction costs increase**: Every trade pays spread + slippage
2. **Large orders penalized**: Slippage grows with order size
3. **High-frequency trading hurt**: Latency makes rapid trading less effective
4. **Capital deployment limited**: Can't use unlimited capital instantly

### Customization

Turn off or adjust features in configuration:

```python
# Minimal costs (idealized backtest)
config = SimulationConfig(
    bid_ask_spread=0.00,
    slippage_per_100_contracts=0.00,
    max_liquidity_per_minute=100000.0,
    latency_minutes=0
)

# High costs (conservative estimate)
config = SimulationConfig(
    bid_ask_spread=0.03,
    slippage_per_100_contracts=0.02,
    max_liquidity_per_minute=200.0,
    latency_minutes=2
)
```

## License

MIT License

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.
