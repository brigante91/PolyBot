"""Historical / context profile — uses local store when available, else conservative defaults."""

from __future__ import annotations

from app.data.historical_store import HistoricalStore
from app.models.candidate import CandidateMarket
from app.models.context import HistoricalProfile


class HistoricalAnalyzer:
    """Build operational profile; extend with API/file backfill later."""

    def __init__(self, store: HistoricalStore | None = None) -> None:
        self._store = store or HistoricalStore()

    def profile(self, candidate: CandidateMarket) -> HistoricalProfile:
        key = candidate.market_id
        snap = self._store.get_summary(key)
        if snap:
            return snap
        vol = candidate.volume or 0.0
        sample = min(500.0, max(10.0, vol / 100.0))
        return HistoricalProfile(
            win_rate_by_strategy={},
            expectancy=0.0,
            max_dd_proxy=0.05,
            fill_quality_avg=0.5,
            regime_label="unknown",
            edge_stability=0.5,
            sample_size=int(sample),
        )
