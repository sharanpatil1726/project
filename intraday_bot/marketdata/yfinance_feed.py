from __future__ import annotations

import datetime as dt
import time
from typing import Optional

import pandas as pd
import yfinance as yf


def fetch_intraday_candles(symbol: str, start: Optional[str] = None, end: Optional[str] = None,
                           period: Optional[str] = "5d", interval: str = "1m") -> pd.DataFrame:
    """Fetch intraday candles using yfinance. Returns a DataFrame with columns: Open, High, Low, Close, Volume."""
    if start or end:
        df = yf.download(symbol, start=start, end=end, interval=interval, auto_adjust=False, progress=False)
    else:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError(f"No data returned for {symbol}")
    df = df.tz_localize(None) if df.index.tz is not None else df
    return df


def poll_latest_candles(symbol: str, interval: str = "1m", lookback_minutes: int = 120,
                         sleep_seconds: int = 60):
    """Generator yielding the latest candles repeatedly, polling yfinance.

    Each iteration yields a DataFrame of the last `lookback_minutes` worth of 1m candles.
    """
    while True:
        end = dt.datetime.utcnow()
        start = end - dt.timedelta(minutes=lookback_minutes + 5)
        df = fetch_intraday_candles(
            symbol,
            start=start.strftime("%Y-%m-%d %H:%M:%S"),
            end=end.strftime("%Y-%m-%d %H:%M:%S"),
            interval=interval,
        )
        yield df.tail(lookback_minutes)
        time.sleep(sleep_seconds)