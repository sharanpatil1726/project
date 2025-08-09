# Intraday Trading Bot (India)

This project provides a modular framework for intraday trading in Indian stock markets with:
- Broker abstraction (paper broker included; plug-ins for real brokers)
- Example SMA crossover strategy
- Risk management (position sizing, ATR-based initial and trailing stop, daily loss cap)
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
- To connect a real broker (e.g., Zerodha Kite, Upstox, Groww), implement a class in `intraday_bot/brokers/` that conforms to `BrokerBase` and wire it in `scripts/run_live.py`.

## Real-time data and Groww

- Real-time market data typically requires a broker/exchange data subscription and an official API. Scraping or using unofficial endpoints can violate terms and law.
- Groww does not publicly provide an official real-time market data API comparable to Zerodha's Kite Ticker at the time of writing. If you have access to Groww's official APIs via a partner program, implement a broker adapter that:
  - Authenticates per their documentation
  - Streams ticks/candles (websocket) or polls endpoints
  - Maps symbols/instrument tokens to NSE/BSE instruments
- If you need production-grade real-time streaming now, consider Zerodha (Kite Connect), Upstox, or FYERS. Implement `BrokerBase` for your provider.

## Trailing Stop Loss (TSL)

- The bot now maintains an ATR-based trailing stop:
  - Longs: stop = last_close - atr_mult * ATR; only ratchets upward
  - Shorts: stop = last_close + atr_mult * ATR; only ratchets downward
  - Stop is checked on each new candle using High/Low to simulate intra-candle hit.

## Project Structure

- `intraday_bot/`: core library
  - `brokers/`: broker interfaces and implementations
  - `marketdata/`: data feeds
  - `strategy/`: strategies
  - `execution.py`: bot orchestration (with trailing stop)
  - `risk.py`: risk and sizing
  - `config.py`: config models
- `scripts/`: CLI entry points

## Compliance & Risk

- In India, deploying fully automated strategies often requires exchange-approved algos. Check your broker's terms and regulations.
- Trading is risky. This code is for educational purposes and comes with no warranty.