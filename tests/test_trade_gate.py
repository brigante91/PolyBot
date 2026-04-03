"""Trade authorization gate: edge, confidence, execution, spread, depth, stale."""

from __future__ import annotations

from datetime import datetime, timezone

from app.analysis.fair_value_engine import FairValueResult
from app.config import RunMode, Settings
from app.decision.trade_gate import NoTradeReason, evaluate_trade_gate
from app.models.candidate import CandidateMarket
from app.models.context import HistoricalProfile, LiveFeatures, MarketContext
from app.models.decision import OperationalAction
from app.models.order import OrderIntent, OrderSide, TimeInForce
from app.strategy.strategy_selector import SelectionResult


def _base_settings(**over: float) -> Settings:
    kwargs = dict(
        mode=RunMode.PAPER,
        enable_live_trading=False,
        max_order_size_usd=25.0,
        max_total_exposure_usd=300.0,
        daily_loss_limit_usd=50.0,
        max_open_orders=10,
        min_gross_edge=0.0025,
        min_net_edge=0.0010,
        min_trade_confidence=0.55,
        min_execution_quality=0.60,
        trade_gate_max_spread_bps=80.0,
        min_depth_usd_trade=25.0,
    )
    kwargs.update(over)
    return Settings(**kwargs)


def _ctx(
    *,
    fv: FairValueResult,
    spread_bps: float = 20.0,
    depth: float = 100.0,
    response_score: float = 0.75,
) -> MarketContext:
    return MarketContext(
        candidate=CandidateMarket(market_id="m1", end_date=datetime.now(timezone.utc)),
        live=LiveFeatures(
            spread_bps=spread_bps,
            depth_top_usd=depth,
            response_score=response_score,
        ),
        historical=HistoricalProfile(),
        score_total=0.8,
        fair_value=fv,
    )


def _fv_buy_edge(*, gross: float, net: float, conf: float = 0.7) -> FairValueResult:
    m = 0.5
    fair = m + gross
    return FairValueResult(
        fair_prob=fair,
        market_prob=m,
        edge=gross,
        edge_net=net,
        confidence=conf,
    )


def _sel_fvg() -> SelectionResult:
    return SelectionResult(
        strategy_id="fair_value_gap",
        confidence=0.7,
        strategy_score=0.7,
        action=OperationalAction.NO_TRADE,
        rationale="test",
    )


def _intent_buy() -> OrderIntent:
    return OrderIntent(
        market_id="m1",
        token_id="tok",
        side=OrderSide.BUY,
        price=0.5,
        size=10.0,
        tif=TimeInForce.GTC,
    )


def test_gate_zero_gross_is_no_trade() -> None:
    s = _base_settings()
    fv = _fv_buy_edge(gross=0.0, net=-0.01)
    g = evaluate_trade_gate(s, _ctx(fv=fv), fv, _sel_fvg(), _intent_buy(), is_stale=False)
    assert g.trade_allowed is False
    assert g.recommended_action == OperationalAction.NO_TRADE
    assert g.reason in (NoTradeReason.EDGE_BELOW_THRESHOLD.value, NoTradeReason.EDGE_NET_NEGATIVE.value)


def test_gate_negative_net_is_no_trade() -> None:
    s = _base_settings()
    fv = _fv_buy_edge(gross=0.01, net=-0.002)
    g = evaluate_trade_gate(s, _ctx(fv=fv), fv, _sel_fvg(), _intent_buy(), is_stale=False)
    assert g.trade_allowed is False
    assert g.reason == NoTradeReason.EDGE_NET_NEGATIVE.value


def test_gate_low_confidence() -> None:
    s = _base_settings()
    fv = _fv_buy_edge(gross=0.01, net=0.005, conf=0.2)
    g = evaluate_trade_gate(s, _ctx(fv=fv), fv, _sel_fvg(), _intent_buy(), is_stale=False)
    assert g.trade_allowed is False
    assert g.reason == NoTradeReason.CONFIDENCE_TOO_LOW.value


def test_gate_low_execution_quality() -> None:
    s = _base_settings()
    fv = _fv_buy_edge(gross=0.01, net=0.005, conf=0.7)
    g = evaluate_trade_gate(
        s,
        _ctx(fv=fv, response_score=0.1),
        fv,
        _sel_fvg(),
        _intent_buy(),
        is_stale=False,
    )
    assert g.trade_allowed is False
    assert g.reason == NoTradeReason.EXECUTION_QUALITY_TOO_LOW.value


def test_gate_all_pass_buy() -> None:
    s = _base_settings()
    fv = _fv_buy_edge(gross=0.012, net=0.008, conf=0.7)
    g = evaluate_trade_gate(s, _ctx(fv=fv), fv, _sel_fvg(), _intent_buy(), is_stale=False)
    assert g.trade_allowed is True
    assert g.recommended_action == OperationalAction.ENTER_LIMIT_BUY
    assert g.reason == "authorized"


def test_gate_regression_edge_zero_no_enter_limit() -> None:
    """Logs must not pair edge≈0 with ENTER_LIMIT_*; gate blocks."""
    s = _base_settings()
    fv = FairValueResult(
        fair_prob=0.5,
        market_prob=0.5,
        edge=0.0,
        edge_net=-0.002,
        confidence=0.61,
    )
    g = evaluate_trade_gate(s, _ctx(fv=fv), fv, _sel_fvg(), _intent_buy(), is_stale=False)
    assert g.trade_allowed is False
    assert g.recommended_action == OperationalAction.NO_TRADE
