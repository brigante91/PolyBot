"""Operational decisions and structured logging payloads."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OperationalAction(str, Enum):
    NO_TRADE = "NO_TRADE"
    PASSIVE_QUOTE = "PASSIVE_QUOTE"
    ENTER_LIMIT_BUY = "ENTER_LIMIT_BUY"
    ENTER_LIMIT_SELL = "ENTER_LIMIT_SELL"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    EXIT = "EXIT"


class MarketDecisionRecord(BaseModel):
    market_id: str
    tradable: bool = True
    rank: int = 0
    selected_strategy: str = "no_trade"
    confidence: float = 0.0
    edge_estimate: float = 0.0
    execution_quality: float = 0.0
    recommended_action: OperationalAction = OperationalAction.NO_TRADE
    recommended_size_usd: float = 0.0
    reason: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
