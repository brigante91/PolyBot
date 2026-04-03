"""Per-market context passed to strategies and risk."""

from __future__ import annotations

from pydantic import BaseModel, Field

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
    candidate: CandidateMarket
    live: LiveFeatures = Field(default_factory=LiveFeatures)
    historical: HistoricalProfile = Field(default_factory=HistoricalProfile)
    score_total: float = 0.0
    rank: int = 0
