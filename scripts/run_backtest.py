from __future__ import annotations

import argparse
import datetime as dt

import pandas as pd

from intraday_bot.brokers.paper import PaperBroker
from intraday_bot.execution import IntradayBot
from intraday_bot.marketdata.yfinance_feed import fetch_intraday_candles
from intraday_bot.risk import RiskManager
from intraday_bot.strategy.sma_crossover import SmaParams


def run(symbol: str, start: str, end: str, fast: int, slow: int, capital: float, risk: float):
    df = fetch_intraday_candles(symbol, start=start, end=end, interval="1m")
    df = df.dropna().copy()

    broker = PaperBroker(slippage_bps=1.0)
    risk_mgr = RiskManager(capital=capital, risk_per_trade=risk)
    bot = IntradayBot(
        symbol=symbol,
        broker=broker,
        risk=risk_mgr,
        square_off_time="15:20",
        strategy_params=SmaParams(fast=fast, slow=slow),
    )

    for i in range(max(fast, slow) + 5, len(df)):
        window = df.iloc[: i + 1]
        bot.on_new_candles(window)

    positions = broker.get_positions()
    orders = broker.get_orders()

    print(f"Backtest complete for {symbol} {start} -> {end}")
    print(f"Final position: {positions.get(symbol, {})}")
    print(f"Realized PnL: {bot.state.realized_pnl:.2f} INR")
    print(f"Number of orders: {len(orders)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run intraday backtest")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--fast", type=int, default=9)
    parser.add_argument("--slow", type=int, default=21)
    parser.add_argument("--capital", type=float, default=200_000)
    parser.add_argument("--risk-per-trade", type=float, default=0.005)
    args = parser.parse_args()

    run(
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        fast=args.fast,
        slow=args.slow,
        capital=args.capital,
        risk=args.risk_per_trade,
    )