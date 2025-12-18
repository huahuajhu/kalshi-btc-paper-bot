"""Daily data collection for BTC prices and Kalshi BTC hourly markets."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, date, time, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional, Tuple

import pandas as pd
import requests


UTC = timezone.utc
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
MS_EPOCH_THRESHOLD = 1_000_000_000_000  # Unix timestamp; values > this (after 2001-09-09 01:46:40 UTC) are treated as milliseconds
CENTS_TO_DOLLARS = 100.0
BINANCE_API_LIMIT = 1000  # Max klines per request per Binance API docs
API_TIMEOUT_SECONDS = 10
PRICE_TOLERANCE = 0.01  # Acceptable deviation when validating YES + NO price sums
MIDNIGHT = time(0, 0)
DOLLAR_THRESHOLD = 1.0
STRIKE_PRICE_FIELDS = ("strike", "strike_price", "strike_price_cents", "functional_strike", "custom_strike", "floor_strike")
YES_PRICE_FIELDS = ("yes_mid", "yes_price", "last_price", "yes_bid", "yes_ask")


def _parse_ts(value: object) -> Optional[datetime]:
    """Parse timestamps from ints (seconds/ms) or strings."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        # Treat large values as milliseconds (common for Kalshi/Binance); otherwise assume seconds.
        if value > MS_EPOCH_THRESHOLD:
            value /= 1000.0
        return datetime.fromtimestamp(value, tz=UTC)

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            return None

    return None


def _normalize_price(value: Optional[float]) -> Optional[float]:
    """Normalize price to dollar units between 0 and 1."""
    if value is None:
        return None
    price = float(value)
    # Kalshi returns cents for many fields.
    if price > DOLLAR_THRESHOLD:
        price = price / CENTS_TO_DOLLARS
    if price < 0 or price > 1:
        return None
    return price


def _extract_strike(market: dict) -> Optional[float]:
    """Pull a strike price from a Kalshi market payload."""
    for key in STRIKE_PRICE_FIELDS:
        if key in market and market[key] is not None:
            strike_val = float(market[key])
            if "cents" in key:
                strike_val /= CENTS_TO_DOLLARS
            return strike_val
    return None


def _extract_yes_price(market: dict) -> Optional[float]:
    """Infer a YES price from market fields."""
    for field in YES_PRICE_FIELDS:
        if field in market and market[field] is not None:
            price = _normalize_price(market[field])
            if price is not None:
                return price

    yes_bid = _normalize_price(market.get("yes_bid"))
    yes_ask = _normalize_price(market.get("yes_ask"))
    if yes_bid is not None and yes_ask is not None:
        return (yes_bid + yes_ask) / 2

    return None


def _format_ts(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _append_csv(df: pd.DataFrame, path: Path, dedup_cols: Iterable[str], sort_cols: Iterable[str]) -> None:
    """Append to CSV with de-duplication and sorting."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = pd.read_csv(path)
        combined = pd.concat([existing, df], ignore_index=True)
    else:
        combined = df.copy()

    combined = combined.drop_duplicates(subset=list(dedup_cols), keep="last")
    combined = combined.sort_values(list(sort_cols))
    combined.to_csv(path, index=False)


def fetch_btc_prices_for_day(target_date: date, symbol: str = "BTCUSDT") -> pd.DataFrame:
    """Fetch minute-level BTC prices for a single UTC day from Binance."""
    start = datetime.combine(target_date, MIDNIGHT, tzinfo=UTC)
    end = min(start + timedelta(days=1), datetime.now(tz=UTC))

    rows = []
    cursor = start
    session = requests.Session()

    while cursor < end:
        params = {
            "symbol": symbol,
            "interval": "1m",
            "startTime": int(cursor.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000),
            "limit": BINANCE_API_LIMIT,
        }
        try:
            resp = session.get(BINANCE_KLINES_URL, params=params, timeout=API_TIMEOUT_SECONDS)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to fetch {symbol} prices from Binance for {target_date}: {exc}") from exc
        klines = resp.json()
        if not klines:
            break

        for entry in klines:
            open_time = datetime.fromtimestamp(entry[0] / 1000, tz=UTC)
            if open_time.date() != target_date or open_time >= end:
                continue
            close_price = float(entry[4])
            rows.append({"timestamp": _format_ts(open_time), "price": close_price})

        # Advance cursor using the last open time.
        last_open = datetime.fromtimestamp(klines[-1][0] / 1000, tz=UTC)
        cursor = last_open + timedelta(minutes=1)

    if not rows:
        return pd.DataFrame(columns=["timestamp", "price"])

    btc_df = pd.DataFrame(rows)
    _validate_btc_prices(btc_df)
    return btc_df


def _is_btc_market(market: dict) -> bool:
    text = " ".join(
        str(market.get(key, "")) for key in ("ticker", "event_ticker", "underlying_ticker", "title", "description")
    ).upper()
    return "BTC" in text or "BITCOIN" in text


def fetch_kalshi_market_data(target_date: date, base_url: Optional[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch Kalshi BTC hourly markets and snapshot YES/NO prices for the given day."""
    base = (base_url or os.getenv("KALSHI_API_BASE") or KALSHI_BASE_URL).rstrip("/")
    token = os.getenv("KALSHI_API_TOKEN")

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    session = requests.Session()
    try:
        resp = session.get(f"{base}/markets", params={"status": "open"}, headers=headers, timeout=API_TIMEOUT_SECONDS)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch Kalshi markets for {target_date}: {exc}") from exc
    payload = resp.json()
    markets = payload.get("markets") or payload.get("data") or []

    market_rows = []
    contract_rows = []
    fetched_at = datetime.now(tz=UTC)

    for market in markets:
        if not _is_btc_market(market):
            continue

        hour_start = _parse_ts(
            market.get("open_time")
            or market.get("start_time")
            or market.get("listed_at")
            or market.get("open_time_unix")
        )
        if hour_start is None or hour_start.date() != target_date:
            continue

        strike_price = _extract_strike(market)
        if strike_price is None:
            continue

        yes_price = _extract_yes_price(market)
        if yes_price is None:
            continue

        yes_price = round(yes_price, 4)
        no_price = round(1 - yes_price, 4)

        market_rows.append(
            {
                "hour_start": _format_ts(hour_start),
                "strike_price": strike_price,
            }
        )

        price_timestamp = _parse_ts(market.get("last_trade_time") or market.get("updated_time")) or fetched_at
        contract_rows.append(
            {
                "timestamp": _format_ts(price_timestamp),
                "strike_price": strike_price,
                "yes_price": yes_price,
                "no_price": no_price,
            }
        )

    markets_df = pd.DataFrame(market_rows, columns=["hour_start", "strike_price"])
    contracts_df = pd.DataFrame(contract_rows, columns=["timestamp", "strike_price", "yes_price", "no_price"])
    _validate_contract_prices(contracts_df)
    return markets_df, contracts_df


class DailyDataCollector:
    """Coordinate daily BTC + Kalshi data collection."""

    def __init__(
        self,
        btc_prices_path: Path = Path("data/btc_prices_minute.csv"),
        markets_path: Path = Path("data/kalshi_markets.csv"),
        contract_prices_path: Path = Path("data/kalshi_contract_prices.csv"),
        kalshi_base_url: Optional[str] = None,
    ) -> None:
        self.btc_prices_path = Path(btc_prices_path)
        self.markets_path = Path(markets_path)
        self.contract_prices_path = Path(contract_prices_path)
        self.kalshi_base_url = kalshi_base_url

    def collect(self, target_date: date, fetch_btc: bool = True, fetch_kalshi: bool = True) -> None:
        if fetch_btc:
            print(f"Fetching BTC minute data for {target_date} (UTC)...")
            btc_df = fetch_btc_prices_for_day(target_date)
            if btc_df.empty:
                raise RuntimeError(
                    f"No BTC prices returned for {target_date} (API unavailable or no intraday data)."
                )
            _append_csv(btc_df, self.btc_prices_path, dedup_cols=["timestamp"], sort_cols=["timestamp"])
            print(f"Saved {len(btc_df)} BTC rows to {self.btc_prices_path}")
        else:
            print("Skipping BTC fetch (per flag).")

        if fetch_kalshi:
            print(f"Fetching Kalshi BTC hourly markets for {target_date} (UTC)...")
            markets_df, contracts_df = fetch_kalshi_market_data(target_date, base_url=self.kalshi_base_url)

            if markets_df.empty:
                raise RuntimeError(
                    f"No Kalshi BTC markets found for {target_date} (API unavailable or no BTC hourly listings)."
                )
            if contracts_df.empty:
                raise RuntimeError(f"No Kalshi BTC contract prices returned for {target_date}")

            _append_csv(markets_df, self.markets_path, dedup_cols=["hour_start", "strike_price"], sort_cols=["hour_start", "strike_price"])
            _append_csv(
                contracts_df,
                self.contract_prices_path,
                dedup_cols=["timestamp", "strike_price"],
                sort_cols=["timestamp", "strike_price"],
            )

            print(
                f"Saved {len(markets_df)} markets to {self.markets_path} "
                f"and {len(contracts_df)} price points to {self.contract_prices_path}"
            )
        else:
            print("Skipping Kalshi fetch (per flag).")


def _validate_btc_prices(df: pd.DataFrame) -> None:
    if df.empty:
        return
    if (df["price"] <= 0).any():
        raise ValueError("BTC prices must be positive")


def _validate_contract_prices(df: pd.DataFrame) -> None:
    if df.empty:
        return
    if (df["yes_price"] < 0).any() or (df["yes_price"] > 1).any():
        raise ValueError("YES prices must be between 0 and 1")
    if (df["no_price"] < 0).any() or (df["no_price"] > 1).any():
        raise ValueError("NO prices must be between 0 and 1")

    price_sum = df["yes_price"] + df["no_price"]
    valid_mask = price_sum.between(1 - PRICE_TOLERANCE, 1 + PRICE_TOLERANCE)
    if not valid_mask.all():
        bad_row = df.loc[~valid_mask].iloc[0]
        raise ValueError(
            f"YES + NO must ≈ 1.00. Example row -> YES: {bad_row['yes_price']}, NO: {bad_row['no_price']}"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect today's BTC + Kalshi market data.")
    parser.add_argument("--date", type=str, help="UTC date to collect (YYYY-MM-DD). Defaults to today (UTC).")
    parser.add_argument("--btc-file", type=Path, default=Path("data/btc_prices_minute.csv"), help="BTC output CSV path.")
    parser.add_argument("--markets-file", type=Path, default=Path("data/kalshi_markets.csv"), help="Kalshi markets CSV path.")
    parser.add_argument(
        "--contracts-file",
        type=Path,
        default=Path("data/kalshi_contract_prices.csv"),
        help="Kalshi contract prices CSV path.",
    )
    parser.add_argument("--skip-btc", action="store_true", help="Skip BTC collection.")
    parser.add_argument("--skip-kalshi", action="store_true", help="Skip Kalshi collection.")
    parser.add_argument("--kalshi-base-url", type=str, default=None, help="Override Kalshi API base URL.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    target_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else datetime.now(tz=UTC).date()

    collector = DailyDataCollector(
        btc_prices_path=args.btc_file,
        markets_path=args.markets_file,
        contract_prices_path=args.contracts_file,
        kalshi_base_url=args.kalshi_base_url,
    )
    collector.collect(target_date=target_date, fetch_btc=not args.skip_btc, fetch_kalshi=not args.skip_kalshi)


if __name__ == "__main__":
    main()
