from __future__ import annotations

from datetime import datetime, timezone

from app.analysis.fair_value_engine import FairValueResult
from app.config import Settings
from app.models.candidate import CandidateMarket
from app.models.context import HistoricalProfile, LiveFeatures, MarketContext
from app.strategy.strategy_selector import StrategySelector


def test_selector_returns_result() -> None:
    s = Settings(
        MODE="paper",
        ENABLE_LIVE_TRADING=False,
        MAX_ORDER_SIZE_USD=25,
        MAX_TOTAL_EXPOSURE_USD=300,
        DAILY_LOSS_LIMIT_USD=50,
        MAX_OPEN_ORDERS=10,
    )
    sel = StrategySelector(s)
    ctx = MarketContext(
        candidate=CandidateMarket(market_id="m", end_date=datetime.now(timezone.utc)),
        live=LiveFeatures(spread_bps=200.0, depth_top_usd=5000.0, mid_change_1m_bps=50.0),
        historical=HistoricalProfile(),
        score_total=0.9,
        fair_value=FairValueResult(
            fair_prob=0.58,
            market_prob=0.52,
            edge=0.06,
            edge_net=0.04,
            confidence=0.72,
        ),
    )
    r = sel.select(ctx)
    assert r.strategy_id in (
        "no_trade",
        "passive_market_making",
        "mean_reversion_micro",
        "momentum_micro",
        "fair_value_gap",
        "inventory_reduction",
    )
    assert hasattr(r, "explain_selected")
    assert hasattr(r, "second_best_id")
