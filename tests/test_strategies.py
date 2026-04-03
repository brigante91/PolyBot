from __future__ import annotations

from app.config import Settings
from app.models.position import Position
from app.strategies import get_strategy


def test_mean_reversion_emits_or_none() -> None:
    s = Settings(
        MODE="paper",
        ENABLE_LIVE_TRADING=False,
        MAX_ORDER_SIZE_USD=25,
        MAX_TOTAL_EXPOSURE_USD=300,
        DAILY_LOSS_LIMIT_USD=50,
        MAX_OPEN_ORDERS=10,
    )
    strat = get_strategy("mean_reversion_micro", settings=s)
    for mid in [0.5 + i * 0.001 for i in range(20)]:
        strat.prepare({"mid": mid})
    state = {
        "market_id": "m",
        "token_id": "t",
        "spread_bps": 50.0,
        "depth_usd": 5000.0,
        "mid": 0.52,
    }
    sig = strat.generate_signal(state)
    assert sig is None or sig.strategy == "mean_reversion_micro"


def test_market_making_healthcheck() -> None:
    s = Settings(
        MODE="paper",
        ENABLE_LIVE_TRADING=False,
        MAX_ORDER_SIZE_USD=25,
        MAX_TOTAL_EXPOSURE_USD=300,
        DAILY_LOSS_LIMIT_USD=50,
        MAX_OPEN_ORDERS=10,
    )
    strat = get_strategy("market_making_passive", settings=s)
    h = strat.healthcheck()
    assert h.get("ok") is True
