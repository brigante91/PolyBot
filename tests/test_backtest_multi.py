from __future__ import annotations

import pandas as pd

from app.backtest.v4_multi_engine import MultiMarketBacktest
from app.config import Settings


def test_multi_market_backtest_runs() -> None:
    s = Settings(MODE="paper")
    n = 15
    m1 = pd.DataFrame(
        {
            "close": [0.5 + 0.01 * i for i in range(n)],
            "spread_bps": [12.0] * n,
            "mom": [0.1 * ((-1) ** i) for i in range(n)],
        }
    )
    m2 = m1.copy()
    eng = MultiMarketBacktest(s)
    r = eng.run(
        {"a": m1, "b": m2},
        strategy_name="mean_reversion_micro",
        bankroll_usd=1000.0,
        max_active_markets=2,
        expiry_bars={"a": 8},
    )
    assert r.bars >= 1
    assert "a" in r.pnl_by_market
