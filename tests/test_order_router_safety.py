"""Order router must not submit when trade_allowed is false or action is NO_TRADE."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.config import RunMode, Settings
from app.execution.order_router import OrderRouter, RoutedIntent
from app.models.decision import OperationalAction
from app.models.order import OrderIntent, OrderSide, TimeInForce
from app.services.execution_service import ExecutionResult, ExecutionService


def _settings() -> Settings:
    return Settings(
        mode=RunMode.PAPER,
        enable_live_trading=False,
        max_order_size_usd=25.0,
        max_total_exposure_usd=300.0,
        daily_loss_limit_usd=50.0,
        max_open_orders=10,
    )


def _intent() -> OrderIntent:
    return OrderIntent(
        market_id="m1",
        token_id="t1",
        side=OrderSide.BUY,
        price=0.5,
        size=1.0,
        tif=TimeInForce.GTC,
    )


def test_router_skips_trade_allowed_false() -> None:
    ex = MagicMock(spec=ExecutionService)
    ex.submit = MagicMock(return_value=ExecutionResult(ok=True))
    r = OrderRouter(_settings(), ex)
    ri = RoutedIntent(
        priority=1.0,
        market_id="m1",
        intent=_intent(),
        book=None,
        strategy_id="fair_value_gap",
        confidence=0.7,
        trade_allowed=False,
        recommended_action=OperationalAction.ENTER_LIMIT_BUY,
    )
    out = r.route_batch([ri], mode=RunMode.PAPER, bankroll_usd=1000.0)
    assert out == []
    ex.submit.assert_not_called()


def test_router_skips_no_trade_action() -> None:
    ex = MagicMock(spec=ExecutionService)
    ex.submit = MagicMock(return_value=ExecutionResult(ok=True))
    r = OrderRouter(_settings(), ex)
    ri = RoutedIntent(
        priority=1.0,
        market_id="m1",
        intent=_intent(),
        book=None,
        strategy_id="fair_value_gap",
        confidence=0.7,
        trade_allowed=True,
        recommended_action=OperationalAction.NO_TRADE,
    )
    out = r.route_batch([ri], mode=RunMode.PAPER, bankroll_usd=1000.0)
    assert out == []
    ex.submit.assert_not_called()
