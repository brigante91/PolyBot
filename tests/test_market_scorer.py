from __future__ import annotations

from datetime import datetime, timezone

from app.analysis.market_scorer import MarketScorer
from app.config import Settings
from app.models.candidate import CandidateMarket
from app.models.context import HistoricalProfile, LiveFeatures


def test_scorer_returns_keys() -> None:
    s = Settings(
        MODE="paper",
        ENABLE_LIVE_TRADING=False,
        MAX_ORDER_SIZE_USD=25,
        MAX_TOTAL_EXPOSURE_USD=300,
        DAILY_LOSS_LIMIT_USD=50,
        MAX_OPEN_ORDERS=10,
    )
    sc = MarketScorer(s)
    c = CandidateMarket(
        market_id="1",
        liquidity=5000.0,
        volume=2000.0,
        end_date=datetime.now(timezone.utc),
    )
    live = LiveFeatures(spread_bps=80.0, depth_top_usd=400.0, response_score=0.8)
    hist = HistoricalProfile(sample_size=50)
    out = sc.score(c, live, hist)
    assert "score_total" in out
    assert "recommended" in out
