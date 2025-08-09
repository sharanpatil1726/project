# Intraday Trading Bot (India)

This project provides a modular framework for intraday trading in Indian stock markets with:
- Broker abstraction (paper broker included; plug-ins for real brokers)
- Example SMA crossover strategy
- Risk management (position sizing, stop loss, daily loss cap)
- Backtesting and simulated live trading scripts

Important: Fully automated order placement in India may require broker/exchange approvals and compliance with SEBI and exchange guidelines. Use paper trading or semi-automated modes unless you have the required approvals. You are responsible for compliance and risk.

## Quick Start

1) Create and activate a virtual environment.

2) Install dependencies:

```bash
pip install -r requirements.txt
```

3) Run a backtest for a NSE equity (using Yahoo Finance data via yfinance; symbol requires `.NS` suffix):

```bash
python scripts/run_backtest.py --symbol RELIANCE.NS --start 2024-04-01 --end 2024-04-30
```

4) Run simulated live trading (paper broker) on the latest intraday data (polled every minute):

```bash
python scripts/run_live.py --symbol TCS.NS --capital 200000 --risk-per-trade 0.005
```

Notes:
- Yahoo Finance data is delayed and not guaranteed accurate; use your broker's market data for live trading.
- To connect a real broker (e.g., Zerodha Kite, Upstox), implement a class in `intraday_bot/brokers/` that conforms to `BrokerBase` and wire it in `scripts/run_live.py`.

## Project Structure

- `intraday_bot/`: core library
  - `brokers/`: broker interfaces and implementations
  - `marketdata/`: data feeds
  - `strategy/`: strategies
  - `execution.py`: bot orchestration
  - `risk.py`: risk and sizing
  - `config.py`: config models
- `scripts/`: CLI entry points

## Compliance & Risk

- In India, deploying fully automated strategies often requires exchange-approved algos. Check your broker's terms and regulations.
- Trading is risky. This code is for educational purposes and comes with no warranty.