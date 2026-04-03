"""Market and token models from Gamma / CLOB."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TokenSide(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class OutcomeToken(BaseModel):
    """Single outcome token (binary market: Yes/No)."""

    token_id: str
    side: TokenSide = TokenSide.UNKNOWN
    outcome_label: str | None = None


class GammaMarket(BaseModel):
    """Normalized Gamma market record."""

    id: str
    slug: str | None = None
    question: str | None = None
    active: bool = True
    closed: bool = False
    liquidity_num: float | None = None
    volume_24hr: float | None = None
    end_date: datetime | None = None
    clob_token_ids: list[str] = Field(default_factory=list)
    outcomes: list[str] | None = None
    tick_size: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    def map_tokens_yes_no(self) -> list[OutcomeToken]:
        """Best-effort Yes/No mapping from outcomes + clob_token_ids."""
        tokens: list[OutcomeToken] = []
        labels = self.outcomes or []
        for i, tid in enumerate(self.clob_token_ids):
            label = labels[i] if i < len(labels) else None
            side = TokenSide.UNKNOWN
            if label:
                low = label.lower()
                if "yes" in low:
                    side = TokenSide.YES
                elif "no" in low:
                    side = TokenSide.NO
            tokens.append(OutcomeToken(token_id=tid, side=side, outcome_label=label))
        return tokens
