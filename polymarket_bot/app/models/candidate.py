"""Unified market candidate representation for multi-market engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.market import OutcomeToken


class CandidateMarket(BaseModel):
    """Output of universe scan + enrichment (minimal fields per PRD)."""

    market_id: str
    question: str = ""
    slug: str | None = None
    tokens: list[OutcomeToken] = Field(default_factory=list)
    active: bool = True
    end_date: datetime | None = None
    category: str | None = None
    liquidity: float | None = None
    volume: float | None = None
    spread_estimate_bps: float | None = None
    tradable: bool = True
    raw: dict[str, Any] = Field(default_factory=dict)

    def primary_token_id(self) -> str | None:
        if self.tokens:
            return self.tokens[0].token_id
        return None

    def condition_id(self) -> str | None:
        """Gamma condition id for CLOB user-channel subscription (if present in raw)."""
        r = self.raw or {}
        cid = r.get("conditionId") or r.get("condition_id")
        if cid is None:
            return None
        s = str(cid).strip()
        return s or None
