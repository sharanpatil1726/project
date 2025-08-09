from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .brokers.base import BrokerBase, Order
from .risk import RiskManager
from .strategy.sma_crossover import SmaParams, generate_signal, compute_atr


@dataclass
class BotState:
    position_qty: int = 0
    average_price: float = 0.0
    realized_pnl: float = 0.0
    stop_price: Optional[float] = None


class IntradayBot:
    def __init__(
        self,
        symbol: str,
        broker: BrokerBase,
        risk: RiskManager,
        square_off_time: str = "15:20",
        strategy_params: Optional[SmaParams] = None,
    ) -> None:
        self.symbol = symbol
        self.broker = broker
        self.risk = risk
        self.square_off_time = square_off_time
        self.state = BotState()
        self.strategy_params = strategy_params or SmaParams()

    def _should_square_off(self, now_ist: Optional[dt.datetime] = None) -> bool:
        if now_ist is None:
            now_ist = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
        cutoff_h, cutoff_m = map(int, self.square_off_time.split(":"))
        cutoff = now_ist.replace(hour=cutoff_h, minute=cutoff_m, second=0, microsecond=0)
        return now_ist >= cutoff

    def _update_trailing_stop(self, candles: pd.DataFrame) -> None:
        if self.state.position_qty == 0:
            self.state.stop_price = None
            return
        atr = compute_atr(candles, self.strategy_params.atr_period).iloc[-1]
        last_close = float(candles["Close"].iloc[-1])
        if self.state.position_qty > 0:
            # Long: raise stop, never lower it
            new_stop = last_close - self.strategy_params.atr_multiplier_sl * atr
            self.state.stop_price = (
                new_stop if self.state.stop_price is None else max(self.state.stop_price, new_stop)
            )
        else:
            # Short: lower stop, never raise it
            new_stop = last_close + self.strategy_params.atr_multiplier_sl * atr
            self.state.stop_price = (
                new_stop if self.state.stop_price is None else min(self.state.stop_price, new_stop)
            )

    def _check_stop_and_exit(self, candles: pd.DataFrame) -> bool:
        if self.state.position_qty == 0 or self.state.stop_price is None:
            return False
        last_low = float(candles["Low"].iloc[-1])
        last_high = float(candles["High"].iloc[-1])
        stop = float(self.state.stop_price)
        if self.state.position_qty > 0 and last_low <= stop:
            # Stop hit for long
            self._sell(self.state.position_qty, stop)
            self.state.stop_price = None
            return True
        if self.state.position_qty < 0 and last_high >= stop:
            # Stop hit for short
            self._buy(abs(self.state.position_qty), stop)
            self.state.stop_price = None
            return True
        return False

    def on_new_candles(self, candles: pd.DataFrame) -> None:
        # candles index assumed chronological
        price = float(candles["Close"].iloc[-1])

        # Square-off logic
        if self._should_square_off():
            self._close_all(price)
            return

        # Enforce existing stop first
        if self._check_stop_and_exit(candles):
            return

        # Strategy signal
        signal, stop_price = generate_signal(candles, self.strategy_params)
        if signal == "FLAT":
            # Maintain trailing stop if in position
            self._update_trailing_stop(candles)
            return

        if stop_price is None:
            # If strategy didn't provide a stop, derive one from ATR
            atr = compute_atr(candles, self.strategy_params.atr_period).iloc[-1]
            stop_price = price - self.strategy_params.atr_multiplier_sl * atr if signal == "BUY" else price + self.strategy_params.atr_multiplier_sl * atr

        # Positioning logic
        if signal == "BUY":
            if self.state.position_qty >= 0:
                qty = self.risk.size_for_trade(price, float(stop_price))
                if qty > 0:
                    self._buy(qty, price)
                    self.state.stop_price = float(stop_price)
            else:
                self._buy(abs(self.state.position_qty), price)
                qty = self.risk.size_for_trade(price, float(stop_price))
                if qty > 0:
                    self._buy(qty, price)
                self.state.stop_price = float(stop_price)
        elif signal == "SELL":
            if self.state.position_qty <= 0:
                qty = self.risk.size_for_trade(price, float(stop_price))
                if qty > 0:
                    self._sell(qty, price)
                    self.state.stop_price = float(stop_price)
            else:
                self._sell(abs(self.state.position_qty), price)
                qty = self.risk.size_for_trade(price, float(stop_price))
                if qty > 0:
                    self._sell(qty, price)
                self.state.stop_price = float(stop_price)

        # After any action, adjust trailing stop with the latest candle
        self._update_trailing_stop(candles)

    def _buy(self, quantity: int, price: float) -> None:
        if quantity <= 0:
            return
        result = self.broker.place_order(
            Order(symbol=self.symbol, side="BUY", quantity=quantity, price=price, tag="entry")
        )
        self._update_position(quantity, result.average_price or price)

    def _sell(self, quantity: int, price: float) -> None:
        if quantity <= 0:
            return
        result = self.broker.place_order(
            Order(symbol=self.symbol, side="SELL", quantity=quantity, price=price, tag="exit" if self.state.position_qty > 0 else "entry")
        )
        self._update_position(-quantity, result.average_price or price)

    def _update_position(self, delta_qty: int, fill_price: float) -> None:
        # Update weighted average price and realized PnL
        old_qty = self.state.position_qty
        new_qty = old_qty + delta_qty
        if old_qty == 0 or (old_qty > 0 and delta_qty > 0) or (old_qty < 0 and delta_qty < 0):
            # Increasing in same direction or entering new position
            self.state.average_price = (
                (self.state.average_price * abs(old_qty) + fill_price * abs(delta_qty))
                / max(abs(new_qty), 1)
            )
        else:
            # Reducing or flipping
            reduce_qty = min(abs(old_qty), abs(delta_qty))
            pnl_per_share = (fill_price - self.state.average_price) * (1 if old_qty > 0 else -1)
            self.state.realized_pnl += pnl_per_share * reduce_qty
            if new_qty == 0:
                self.state.average_price = 0.0
            else:
                # Flipped; average becomes fill
                if (old_qty > 0 and delta_qty < 0 and abs(delta_qty) > abs(old_qty)) or (
                    old_qty < 0 and delta_qty > 0 and abs(delta_qty) > abs(old_qty)
                ):
                    self.state.average_price = fill_price
        self.state.position_qty = new_qty

    def _close_all(self, price: float) -> None:
        if self.state.position_qty > 0:
            self._sell(self.state.position_qty, price)
        elif self.state.position_qty < 0:
            self._buy(abs(self.state.position_qty), price)
        self.state.stop_price = None