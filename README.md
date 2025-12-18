# Kalshi BTC Paper Trading Simulator

Simulate paper trading on Kalshi hourly BTC price markets with different trading strategies.

## Overview

This simulator allows you to backtest trading strategies on Kalshi's hourly BTC price prediction markets. Each hour represents a separate market with multiple strike prices at $250 intervals. The simulator executes minute-by-minute trades and calculates PnL at market resolution.

## Features

- **Hourly Markets**: Each hour (e.g., 1pm-2pm) is a separate market
- **Strike Buckets**: Markets are available at $250 price intervals
- **Market Selection**: Automatically selects the closest strike to BTC spot price at hour start
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
   - Closest strike price is selected from available markets
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
│   └── strategies/               # Trading strategies
│       ├── base.py              # Abstract strategy class
│       ├── momentum.py          # Momentum strategy
│       ├── mean_reversion.py   # Mean reversion strategy
│       └── no_trade.py         # Baseline (no trades)
│
├── notebooks/                     # Analysis notebooks
│   └── analysis.ipynb            # Performance analysis
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

## Example Output

```
============================================================
Strategy Comparison
============================================================
strategy_name  total_pnl  return_pct  final_balance  total_trades  wins  losses  win_rate
MeanReversion   40529.57      405.30       50529.57            45    16      29     35.56
      NoTrade       0.00        0.00       10000.00             0     0       0      0.00
     Momentum       0.00        0.00       10000.00             0     0       0      0.00
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
