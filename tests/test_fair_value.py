from __future__ import annotations

from app.analysis.fair_value_engine import FairValueEngine, FairValueInputs


def test_fair_value_monotonic() -> None:
    f = FairValueEngine(fee_bps=10.0, slippage_bps=5.0)
    r = f.estimate(
        FairValueInputs(
            market_mid=0.5,
            time_to_expiry_years=0.01,
            price_velocity=0.0,
            volatility_annual=0.5,
            book_imbalance=0.1,
        )
    )
    assert 0.0 < r.fair_prob < 1.0
    assert isinstance(r.edge, float)
