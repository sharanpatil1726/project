from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .brokers.base import BrokerBase, Order
from .risk import RiskManager
from .strategy.sma_crossover import SmaParams, generate_signal


@dataclass
class BotState:
    position_qty: int = 0
    average_price: float = 0.0
    realized_pnl: float = 0.0


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

    def on_new_candles(self, candles: pd.DataFrame) -> None:
        # candles index assumed chronological
        price = float(candles["Close"].iloc[-1])

        # Square-off logic
        if self._should_square_off():
            self._close_all(price)
            return

        # Strategy signal
        signal, stop_price = generate_signal(candles, self.strategy_params)
        if signal == "FLAT" or stop_price is None:
            return

        # Positioning logic
        if signal == "BUY":
            if self.state.position_qty >= 0:
                # Add/enter long
                qty = self.risk.size_for_trade(price, stop_price)
                if qty > 0:
                    self._buy(qty, price)
            else:
                # Reduce or flip from short to long
                self._buy(abs(self.state.position_qty), price)
                qty = self.risk.size_for_trade(price, stop_price)
                if qty > 0:
                    self._buy(qty, price)
        elif signal == "SELL":
            if self.state.position_qty <= 0:
                qty = self.risk.size_for_trade(price, stop_price)
                if qty > 0:
                    self._sell(qty, price)
            else:
                # Reduce or flip from long to short
                self._sell(abs(self.state.position_qty), price)
                qty = self.risk.size_for_trade(price, stop_price)
                if qty > 0:
                    self._sell(qty, price)

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
            Order(symbol=self.symbol, side="SELL", quantity=quantity, price=price, tag="entry")
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