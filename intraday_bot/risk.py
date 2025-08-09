from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskManager:
    capital: float
    risk_per_trade: float  # fraction, e.g., 0.005 for 0.5%
    daily_max_loss_fraction: float = 0.02
    max_position_qty: Optional[int] = None

    def max_loss_today_reached(self, realized_pnl: float) -> bool:
        return realized_pnl <= -self.capital * self.daily_max_loss_fraction

    def size_for_trade(self, entry_price: float, stop_price: float) -> int:
        risk_amount = self.capital * self.risk_per_trade
        per_share_risk = abs(entry_price - stop_price)
        if per_share_risk <= 0:
            return 0
        qty = int(risk_amount // per_share_risk)
        if self.max_position_qty is not None:
            qty = min(qty, self.max_position_qty)
        return max(qty, 0)