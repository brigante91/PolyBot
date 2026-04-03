"""Portfolio position."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Position(BaseModel):
    market_id: str
    token_id: str
    size: float = 0.0
    avg_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    meta: dict = Field(default_factory=dict)
