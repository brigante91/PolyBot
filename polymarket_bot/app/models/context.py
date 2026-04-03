"""Per-market context passed to strategies and risk."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from app.analysis.fair_value_engine import FairValueEngine, FairValueInputs, FairValueResult
from app.models.candidate import CandidateMarket
from app.models.orderbook import OrderBookSnapshot


class LiveFeatures(BaseModel):
    best_bid: float | None = None
    best_ask: float | None = None
    spread_abs: float | None = None
    spread_bps: float | None = None
    depth_top_usd: float = 0.0
    book_imbalance: float = 0.0
    mid_change_1m_bps: float = 0.0
    update_rate_hz: float = 0.0
    recent_trade_count: int = 0
    response_score: float = 0.5
    book: OrderBookSnapshot | None = None


class HistoricalProfile(BaseModel):
    """Synthesized from historical_analyzer; may be partial without deep history."""

    win_rate_by_strategy: dict[str, float] = Field(default_factory=dict)
    expectancy: float = 0.0
    max_dd_proxy: float = 0.0
    fill_quality_avg: float = 0.5
    regime_label: str = "unknown"
    edge_stability: float = 0.5
    sample_size: int = 0


class MarketContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    candidate: CandidateMarket
    live: LiveFeatures = Field(default_factory=LiveFeatures)
    historical: HistoricalProfile = Field(default_factory=HistoricalProfile)
    score_total: float = 0.0
    rank: int = 0
    fair_value: FairValueResult | None = None

    def compute_fair_value(
        self,
        engine: FairValueEngine,
        *,
        underlying_price: float | None = None,
        price_to_beat: float | None = None,
    ) -> FairValueResult:
        """Attach probabilistic fair value from live book and time to expiry."""
        mid = self.live.book.mid() if self.live.book else 0.5
        ttr_y = 1e-6
        if self.candidate.end_date:
            now = datetime.now(timezone.utc)
            end = self.candidate.end_date
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            ttr_y = max(1e-10, (end - now).total_seconds() / (365.25 * 86400.0))
        return engine.estimate(
            FairValueInputs(
                market_mid=float(mid or 0.5),
                underlying_price=underlying_price,
                price_to_beat=price_to_beat,
                time_to_expiry_years=ttr_y,
                price_velocity=self.live.mid_change_1m_bps / 10000.0,
                volatility_annual=0.55,
                book_imbalance=self.live.book_imbalance,
                distance_from_mid_bps=0.0,
            )
        )
