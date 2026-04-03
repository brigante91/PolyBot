"""Strategy signals and exit decisions."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SignalAction(str, Enum):
    NONE = "none"
    QUOTE_BID = "quote_bid"
    QUOTE_ASK = "quote_ask"
    BUY = "buy"
    SELL = "sell"


class Signal(BaseModel):
    strategy: str
    market_id: str
    token_id: str
    action: SignalAction
    price: float | None = None
    size: float | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class ExitDecision(BaseModel):
    should_exit: bool = False
    reason: str = ""
    limit_price: float | None = None
