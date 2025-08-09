from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional

from .base import BrokerBase, Order, OrderResult


@dataclass
class Position:
    quantity: int = 0
    average_price: float = 0.0


class PaperBroker(BrokerBase):
    def __init__(self, slippage_bps: float = 1.0) -> None:
        self._positions: Dict[str, Position] = {}
        self._orders: Dict[str, Dict] = {}
        self._slippage_bps = slippage_bps

    def connect(self) -> None:  # noqa: D401
        """No-op connect for paper broker."""
        return None

    def place_order(self, order: Order) -> OrderResult:
        order_id = str(uuid.uuid4())
        # Simulate fill at given price or at market with small slippage
        fill_price = order.price if order.price is not None else None
        if fill_price is None:
            # If caller did not provide a reference price, we cannot guess;
            # require callers to pass a price from latest tick or candle close.
            raise ValueError(
                "PaperBroker requires order.price for deterministic fills in simulations"
            )
        # Apply slippage
        slip_multiplier = 1.0 + (self._slippage_bps / 10000.0) * (1 if order.side == "BUY" else -1)
        avg_price = round(fill_price * slip_multiplier, 2)

        # Update position
        pos = self._positions.get(order.symbol, Position())
        signed_qty = order.quantity if order.side == "BUY" else -order.quantity
        new_qty = pos.quantity + signed_qty
        if pos.quantity == 0:
            new_avg = avg_price
        elif (pos.quantity > 0 and signed_qty > 0) or (pos.quantity < 0 and signed_qty < 0):
            new_avg = (pos.average_price * abs(pos.quantity) + avg_price * abs(signed_qty)) / (
                abs(pos.quantity) + abs(signed_qty)
            )
        else:
            # Reducing or flipping position; if flip, average becomes fill price
            if (pos.quantity + signed_qty) == 0:
                new_avg = 0.0
            elif (pos.quantity > 0 and signed_qty < 0 and abs(signed_qty) > pos.quantity) or (
                pos.quantity < 0 and signed_qty > 0 and abs(signed_qty) > abs(pos.quantity)
            ):
                new_avg = avg_price
            else:
                new_avg = pos.average_price
        self._positions[order.symbol] = Position(quantity=new_qty, average_price=new_avg)

        result = OrderResult(order_id=order_id, status="FILLED", average_price=avg_price)
        self._orders[order_id] = {
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "average_price": avg_price,
            "status": "FILLED",
            "timestamp": time.time(),
            "tag": order.tag,
        }
        return result

    def cancel_all(self, symbol: Optional[str] = None) -> None:  # noqa: D401
        """No open orders in this immediate fill simulation."""
        return None

    def get_positions(self) -> Dict[str, Dict]:
        out: Dict[str, Dict] = {}
        for symbol, pos in self._positions.items():
            out[symbol] = {"quantity": pos.quantity, "average_price": pos.average_price}
        return out

    def get_orders(self) -> Dict[str, Dict]:
        return self._orders.copy()