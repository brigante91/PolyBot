from __future__ import annotations

from datetime import timedelta

from app.config import RunMode
from app.models.order import OrderIntent, OrderSide, TimeInForce
from app.models.orderbook import BookLevel, OrderBookSnapshot
from app.models.risk import RejectReason
from app.risk.risk_engine import RiskEngine
from app.utils.time import utc_now


def test_kill_switch_blocks(settings) -> None:
    settings.kill_switch = True
    r = RiskEngine(settings)
    intent = OrderIntent(
        market_id="m1",
        token_id="t1",
        side=OrderSide.BUY,
        price=0.5,
        size=10,
        tif=TimeInForce.GTC,
    )
    book = OrderBookSnapshot(
        token_id="t1",
        bids=[BookLevel(price=0.49, size=100)],
        asks=[BookLevel(price=0.51, size=100)],
        fetched_at=utc_now(),
    )
    res = r.check_pre_trade(
        intent,
        mode=RunMode.PAPER,
        book=book,
        notional_usd=5.0,
        is_adding_to_loser=False,
    )
    assert not res.allowed
    assert res.reason == RejectReason.KILL_SWITCH


def test_stale_data_rejected(settings) -> None:
    r = RiskEngine(settings)
    old = utc_now() - timedelta(seconds=100)
    book = OrderBookSnapshot(
        token_id="t1",
        bids=[BookLevel(price=0.49, size=100)],
        asks=[BookLevel(price=0.51, size=100)],
        fetched_at=old,
    )
    intent = OrderIntent(
        market_id="m1",
        token_id="t1",
        side=OrderSide.BUY,
        price=0.5,
        size=10,
        tif=TimeInForce.GTC,
    )
    res = r.check_pre_trade(
        intent,
        mode=RunMode.PAPER,
        book=book,
        notional_usd=5.0,
        is_adding_to_loser=False,
    )
    assert not res.allowed
    assert res.reason == RejectReason.STALE_DATA


def test_spread_too_wide(settings) -> None:
    settings.max_spread_bps = 10
    r = RiskEngine(settings)
    book = OrderBookSnapshot(
        token_id="t1",
        bids=[BookLevel(price=0.4, size=100)],
        asks=[BookLevel(price=0.6, size=100)],
        fetched_at=utc_now(),
    )
    intent = OrderIntent(
        market_id="m1",
        token_id="t1",
        side=OrderSide.BUY,
        price=0.5,
        size=10,
        tif=TimeInForce.GTC,
    )
    res = r.check_pre_trade(
        intent,
        mode=RunMode.PAPER,
        book=book,
        notional_usd=5.0,
        is_adding_to_loser=False,
    )
    assert not res.allowed
    assert res.reason == RejectReason.SPREAD_TOO_WIDE
