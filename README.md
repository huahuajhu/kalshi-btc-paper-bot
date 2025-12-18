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

# Configure environment (optional)
cp .env.example .env
# Edit .env to customize data sources and paths
```

## Usage

### Data Collection (New! 📊)

Collect today's BTC prices and generate Kalshi market data:

```bash
# Run the full daily data collection pipeline
python scripts/collect_daily_data.py

# Or run individual collection scripts:
python scripts/collect_btc_prices.py      # Fetch BTC prices from exchanges
python scripts/collect_kalshi_data.py     # Generate Kalshi market data
```

**What it does:**
- Fetches today's minute-level BTC prices from Binance/Coinbase (via CCXT)
- Generates simulated Kalshi hourly markets with $250 strike intervals
- Generates YES/NO contract prices minute-by-minute
- Validates and appends data to CSV files in `data/`
- No credentials required for BTC prices (public API)

See [`scripts/README.md`](scripts/README.md) for detailed documentation.

### Running Simulations

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
├── scripts/                       # Data collection scripts (NEW!)
│   ├── collect_daily_data.py     # Main pipeline orchestrator
│   ├── collect_btc_prices.py     # Fetch BTC prices via CCXT
│   ├── collect_kalshi_data.py    # Generate Kalshi market data
│   └── README.md                 # Collection scripts documentation
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
    starting_balance=10000.0,       # Starting capital
    max_position_pct=0.1,           # Max 10% per trade
    fee_per_contract=0.0,           # Trading fees
    btc_price_interval=250,         # Strike interval ($250)
    market_duration_minutes=60,     # 1 hour markets
    min_trade_price=0.01,          # Min contract price
    max_trade_price=0.99,          # Max contract price
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

## License

MIT License

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.
