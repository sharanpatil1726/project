from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import pandas as pd


Signal = Literal["BUY", "SELL", "FLAT"]


@dataclass
class SmaParams:
    fast: int = 9
    slow: int = 21
    atr_period: int = 14
    atr_multiplier_sl: float = 2.0


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    close = df["Close"].shift(1)
    tr = pd.concat([
        (high - low),
        (high - close).abs(),
        (low - close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    return atr


def generate_signal(df: pd.DataFrame, params: Optional[SmaParams] = None) -> tuple[Signal, Optional[float]]:
    """Return (signal, stop_loss_price).

    - signal: BUY, SELL, or FLAT (hold)
    - stop_loss_price: suggested stop based on ATR
    """
    if params is None:
        params = SmaParams()
    if len(df) < max(params.fast, params.slow) + 5:
        return "FLAT", None

    close = df["Close"]
    fast = close.rolling(params.fast).mean()
    slow = close.rolling(params.slow).mean()
    atr = compute_atr(df, params.atr_period)

    # Use last two values to detect fresh cross
    if fast.iloc[-2] <= slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1]:
        # Bullish cross
        stop = df["Close"].iloc[-1] - params.atr_multiplier_sl * atr.iloc[-1]
        return "BUY", float(stop)
    if fast.iloc[-2] >= slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1]:
        # Bearish cross
        stop = df["Close"].iloc[-1] + params.atr_multiplier_sl * atr.iloc[-1]
        return "SELL", float(stop)

    return "FLAT", None