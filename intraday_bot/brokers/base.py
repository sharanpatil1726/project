from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class Order:
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: int
    order_type: str = "MARKET"  # MARKET or LIMIT
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    tag: Optional[str] = None


@dataclass
class OrderResult:
    order_id: str
    status: str  # e.g., 'FILLED', 'REJECTED', 'OPEN'
    average_price: Optional[float]


TickerCallback = Callable[[Dict], None]


class BrokerBase(ABC):
    @abstractmethod
    def connect(self) -> None:
        """Establish session, authenticate, and prepare for trading."""

    @abstractmethod
    def place_order(self, order: Order) -> OrderResult:
        """Place an order and return result."""

    @abstractmethod
    def cancel_all(self, symbol: Optional[str] = None) -> None:
        """Cancel all open orders, optionally filtered by symbol."""

    @abstractmethod
    def get_positions(self) -> Dict[str, Dict]:
        """Return current positions keyed by symbol."""

    @abstractmethod
    def get_orders(self) -> Dict[str, Dict]:
        """Return recent orders keyed by id."""

    def subscribe_ticks(self, symbols: list[str], callback: TickerCallback) -> None:
        """Optional: subscribe to live ticks. Default: not implemented."""
        raise NotImplementedError("This broker does not implement tick streaming.")