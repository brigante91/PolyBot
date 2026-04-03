"""Order intents and status."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TimeInForce(str, Enum):
    GTC = "GTC"
    GTD = "GTD"
    FOK = "FOK"
    FAK = "FAK"


class OrderIntent(BaseModel):
    """Limit order intent (internal representation before CLOB submission)."""

    market_id: str
    token_id: str
    side: OrderSide
    price: float
    size: float
    tif: TimeInForce = TimeInForce.GTC
    good_til: datetime | None = None
    client_order_id: str | None = None
    idempotency_key: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
