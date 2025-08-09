from __future__ import annotations

import argparse
import signal
import sys
import time

from intraday_bot.brokers.paper import PaperBroker
from intraday_bot.execution import IntradayBot
from intraday_bot.marketdata.yfinance_feed import poll_latest_candles
from intraday_bot.risk import RiskManager
from intraday_bot.strategy.sma_crossover import SmaParams


_shutdown = False


def _handle_sigint(signum, frame):
    global _shutdown
    _shutdown = True


def run(symbol: str, capital: float, risk: float, fast: int, slow: int, polling_seconds: int):
    signal.signal(signal.SIGINT, _handle_sigint)

    broker = PaperBroker(slippage_bps=1.0)
    risk_mgr = RiskManager(capital=capital, risk_per_trade=risk)
    bot = IntradayBot(
        symbol=symbol,
        broker=broker,
        risk=risk_mgr,
        square_off_time="15:20",
        strategy_params=SmaParams(fast=fast, slow=slow),
    )

    print(f"Starting simulated live trading for {symbol}. Press Ctrl+C to stop.")

    for candles in poll_latest_candles(symbol=symbol, interval="1m", sleep_seconds=polling_seconds):
        if _shutdown:
            break
        try:
            bot.on_new_candles(candles)
            pos = broker.get_positions().get(symbol, {"quantity": 0, "average_price": 0.0})
            print(
                f"Last close={candles['Close'].iloc[-1]:.2f} | Pos={pos['quantity']} @ {pos['average_price']} | PnL={bot.state.realized_pnl:.2f}"
            )
        except Exception as e:
            print(f"Error in loop: {e}")
        time.sleep(1)

    print("Shutting down. Flattening any open positions...")
    # Use latest candle close to close position in paper broker
    last_price = candles["Close"].iloc[-1]
    if bot.state.position_qty > 0:
        bot._sell(bot.state.position_qty, last_price)
    elif bot.state.position_qty < 0:
        bot._buy(abs(bot.state.position_qty), last_price)
    print(f"Final PnL: {bot.state.realized_pnl:.2f} INR")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run simulated live intraday trading")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--capital", type=float, default=200_000)
    parser.add_argument("--risk-per-trade", type=float, default=0.005)
    parser.add_argument("--fast", type=int, default=9)
    parser.add_argument("--slow", type=int, default=21)
    parser.add_argument("--polling-seconds", type=int, default=60)
    args = parser.parse_args()

    run(
        symbol=args.symbol,
        capital=args.capital,
        risk=args.risk_per_trade,
        fast=args.fast,
        slow=args.slow,
        polling_seconds=args.polling_seconds,
    )