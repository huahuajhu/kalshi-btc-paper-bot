# Data Collection Scripts

This directory contains scripts for daily data collection for the Kalshi BTC paper trading simulator.

## Scripts

### `collect_daily_data.py` (Main Entry Point)
Orchestrates the entire data collection pipeline. Run this script daily to collect all required data.

```bash
python scripts/collect_daily_data.py
```

### `collect_btc_prices.py`
Fetches today's BTC minute-level prices from public crypto exchanges (Binance or Coinbase) using the CCXT library.

**Features:**
- Fetches 1-minute OHLCV data for BTC/USDT
- Uses close price as the BTC spot price
- Validates data format and content
- Appends to `data/btc_prices_minute.csv` (removes duplicates)

**Usage:**
```bash
python scripts/collect_btc_prices.py
```

### `collect_kalshi_data.py`
Generates simulated Kalshi market data based on BTC prices.

**Features:**
- Generates hourly markets with strike prices at $250 intervals
- Simulates YES/NO contract prices minute-by-minute
- Ensures YES + NO = 1.00 for all prices
- Appends to `data/kalshi_markets.csv` and `data/kalshi_contract_prices.csv`

**Usage:**
```bash
python scripts/collect_kalshi_data.py
```

**Note:** This script requires BTC price data to be collected first.

## Configuration

Scripts use environment variables from `.env` file (or defaults):

```bash
# Copy the example file
cp .env.example .env

# Edit configuration
BTC_EXCHANGE=binance          # or 'coinbase'
DATA_DIR=data
BTC_PRICES_FILE=data/btc_prices_minute.csv
KALSHI_MARKETS_FILE=data/kalshi_markets.csv
KALSHI_CONTRACT_PRICES_FILE=data/kalshi_contract_prices.csv
```

## Data Flow

```
1. collect_btc_prices.py
   └─> Fetch from Binance/Coinbase API
   └─> Validate and format data
   └─> Append to data/btc_prices_minute.csv

2. collect_kalshi_data.py
   └─> Read BTC prices
   └─> Generate hourly markets (strikes at $250 intervals)
   └─> Generate YES/NO prices minute-by-minute
   └─> Append to data/kalshi_markets.csv
   └─> Append to data/kalshi_contract_prices.csv
```

## Scheduling (Optional)

### Using Cron (Linux/Mac)
Run daily at midnight UTC:

```bash
# Edit crontab
crontab -e

# Add this line (adjust path to your project)
0 0 * * * cd /path/to/kalshi-btc-paper-bot && /usr/bin/python3 scripts/collect_daily_data.py >> logs/collection.log 2>&1
```

### Using Task Scheduler (Windows)
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to "Daily"
4. Set action to run: `python scripts/collect_daily_data.py`

### Using GitHub Actions
See `.github/workflows/daily-data-collection.yml` for automated daily runs.

## Troubleshooting

### "No module named 'ccxt'"
Install dependencies:
```bash
pip install -r requirements.txt
```

### "Exchange rate limit exceeded"
The scripts have built-in rate limiting. If you still hit limits:
- Use a different exchange (set `BTC_EXCHANGE=coinbase`)
- Add delays between runs
- Check exchange API status

### "No BTC data for today"
Run `collect_btc_prices.py` first before `collect_kalshi_data.py`:
```bash
python scripts/collect_btc_prices.py
python scripts/collect_kalshi_data.py
```

Or use the main script which handles the order automatically:
```bash
python scripts/collect_daily_data.py
```

## Data Validation

All scripts validate data before saving:

**BTC Prices:**
- ✓ Required columns: `timestamp`, `price`
- ✓ Prices must be positive
- ✓ No duplicate timestamps
- ✓ Valid timestamp format

**Kalshi Markets:**
- ✓ Required columns: `hour_start`, `strike_price`
- ✓ Strike prices at $250 intervals
- ✓ Valid hour boundaries

**Contract Prices:**
- ✓ Required columns: `timestamp`, `strike_price`, `yes_price`, `no_price`
- ✓ YES + NO must equal 1.00 (±0.01 tolerance)
- ✓ Prices between 0.01 and 0.99
- ✓ Consistent with hourly markets

## Output Files

### `data/btc_prices_minute.csv`
```csv
timestamp,price
2025-01-01 13:00:00,86510
2025-01-01 13:01:00,86540
```

### `data/kalshi_markets.csv`
```csv
hour_start,strike_price
2025-01-01 13:00:00,86250
2025-01-01 13:00:00,86500
```

### `data/kalshi_contract_prices.csv`
```csv
timestamp,strike_price,yes_price,no_price
2025-01-01 13:00:00,86500,0.52,0.48
2025-01-01 13:01:00,86500,0.55,0.45
```
