from __future__ import annotations

from app.risk.position_sizer import PositionSizer


def test_position_sizer_caps(settings) -> None:
    s = PositionSizer(settings)
    sz = s.size_usd(bankroll_usd=10000, confidence=1.0, spread_bps=50.0, mid_price=0.5)
    assert sz <= settings.max_order_size_usd
    assert sz > 0


def test_wide_spread_reduces_size(settings) -> None:
    s = PositionSizer(settings)
    tight = s.size_usd(bankroll_usd=10000, confidence=0.8, spread_bps=20.0, mid_price=0.5)
    wide = s.size_usd(bankroll_usd=10000, confidence=0.8, spread_bps=400.0, mid_price=0.5)
    assert wide <= tight
