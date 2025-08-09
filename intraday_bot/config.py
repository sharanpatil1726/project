from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field
import yaml


class BrokerConfig(BaseModel):
    name: str = Field(description="Broker identifier, e.g., 'paper', 'zerodha', 'upstox'")
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    user_id: Optional[str] = None
    extra: dict = Field(default_factory=dict)


class RiskConfig(BaseModel):
    capital: float = Field(description="Account capital in INR")
    risk_per_trade: float = Field(
        description="Fraction of capital risked per trade, e.g., 0.005 for 0.5%",
        ge=0.0,
        le=0.05,
    )
    daily_max_loss_fraction: float = Field(
        default=0.02, description="Daily loss cap as a fraction of capital"
    )
    max_position_qty: Optional[int] = Field(
        default=None, description="Optional hard cap on quantity per instrument"
    )


class StrategyConfig(BaseModel):
    name: str = Field(description="Strategy name, e.g., 'sma_crossover'")
    params: dict = Field(default_factory=dict)


class LiveConfig(BaseModel):
    symbol: str = Field(description="Instrument symbol, e.g., 'RELIANCE.NS'")
    timeframe: str = Field(default="1m", description="Candle timeframe")
    square_off_time: str = Field(
        default="15:20", description="HH:MM 24h, time to flatten positions before close"
    )
    polling_seconds: int = Field(
        default=60,
        description="Polling frequency for data feed when websockets aren't used",
    )


class AppConfig(BaseModel):
    broker: BrokerConfig
    risk: RiskConfig
    strategy: StrategyConfig
    live: LiveConfig


def load_config_from_yaml(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppConfig(**raw)