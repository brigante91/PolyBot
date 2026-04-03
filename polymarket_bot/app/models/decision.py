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
    # Not named ``event``: structlog reserves ``event`` (first log arg + kwargs collide on **model_dump()).
    decision_event: str = Field(default="decision", serialization_alias="event")
    market_id: str
    tradable: bool = True
    rank: int = 0
    selected_strategy: str = "no_trade"
    second_best_strategy: str = ""
    confidence: float = 0.0
    fair_prob: float | None = None
    market_prob: float | None = None
    edge_gross: float | None = None
    estimated_cost: float | None = None
    edge_net: float | None = None
    threshold_net: float = 0.0
    edge_estimate: float = 0.0
    execution_quality: float = 0.0
    trade_allowed: bool = False
    recommended_action: OperationalAction = OperationalAction.NO_TRADE
    recommended_size_usd: float = 0.0
    reason: str = ""
    strategy_rationale: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
