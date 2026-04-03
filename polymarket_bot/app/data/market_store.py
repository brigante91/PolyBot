"""Per-market state: metadata, score, strategy, orders, last signal, reject reason."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.models.candidate import CandidateMarket
from app.models.decision import OperationalAction


@dataclass
class MarketRuntimeState:
    market_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score_live: float = 0.0
    historical_digest: dict[str, Any] = field(default_factory=dict)
    assigned_strategy: str = "no_trade"
    open_order_ids: list[str] = field(default_factory=list)
    position_size: float = 0.0
    last_signal: str | None = None
    last_reject_reason: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MarketStateStore:
    def __init__(self) -> None:
        self._by_id: dict[str, MarketRuntimeState] = {}

    def get(self, market_id: str) -> MarketRuntimeState | None:
        return self._by_id.get(market_id)

    def upsert_candidate(self, c: CandidateMarket) -> MarketRuntimeState:
        st = self._by_id.get(c.market_id) or MarketRuntimeState(market_id=c.market_id)
        st.metadata = {"question": c.question, "slug": c.slug}
        st.updated_at = datetime.now(timezone.utc)
        self._by_id[c.market_id] = st
        return st

    def update_decision(
        self,
        market_id: str,
        *,
        strategy: str,
        score: float,
        action: OperationalAction,
        reason: str,
    ) -> None:
        st = self._by_id.setdefault(market_id, MarketRuntimeState(market_id=market_id))
        st.assigned_strategy = strategy
        st.score_live = score
        st.last_signal = action.value
        st.last_reject_reason = reason if action == OperationalAction.NO_TRADE else None
        st.updated_at = datetime.now(timezone.utc)
