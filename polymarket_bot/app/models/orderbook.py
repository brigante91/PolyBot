"""Order book snapshots."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class BookLevel(BaseModel):
    price: float
    size: float


class OrderBookSnapshot(BaseModel):
    token_id: str
    bids: list[BookLevel] = Field(default_factory=list)
    asks: list[BookLevel] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    def mid(self) -> float | None:
        bb, ba = self.best_bid, self.best_ask
        if bb is None or ba is None:
            return None
        return (bb + ba) / 2.0

    def spread_bps(self) -> float | None:
        mid = self.mid()
        bb, ba = self.best_bid, self.best_ask
        if mid is None or mid <= 0 or bb is None or ba is None:
            return None
        return (ba - bb) / mid * 10000.0
