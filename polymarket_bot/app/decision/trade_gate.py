"""Hard gate between strategy selection and order intent / routing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.analysis.fair_value_engine import FairValueResult
from app.config import Settings
from app.models.context import MarketContext
from app.models.decision import OperationalAction
from app.models.order import OrderIntent, OrderSide
from app.strategy.strategy_selector import SelectionResult


class NoTradeReason(str, Enum):
    """Standardized NO_TRADE reasons (logs, TUI, metrics)."""

    EDGE_BELOW_THRESHOLD = "edge_below_threshold"
    EDGE_NET_NEGATIVE = "edge_net_negative"
    CONFIDENCE_TOO_LOW = "confidence_too_low"
    EXECUTION_QUALITY_TOO_LOW = "execution_quality_too_low"
    SPREAD_TOO_WIDE = "spread_too_wide"
    DEPTH_TOO_LOW = "depth_too_low"
    MARKET_STALE = "market_stale"
    RISK_BLOCKED = "risk_blocked"
    FEED_DEGRADED = "feed_degraded"
    STRATEGY_NOT_APPLICABLE = "strategy_not_applicable"
    NO_INTENT = "no_intent"


@dataclass
class TradeGateResult:
    trade_allowed: bool
    recommended_action: OperationalAction
    reason: str
    edge_gross: float | None
    edge_net: float | None
    fair_prob: float | None
    market_prob: float | None
    estimated_cost: float | None
    confidence: float
    execution_quality: float
    threshold_net: float
    risk_passed: bool
    execution_passed: bool
    passive_quote: bool


def evaluate_trade_gate(
    settings: Settings,
    ctx: MarketContext,
    fv: FairValueResult | None,
    sel: SelectionResult,
    intent: OrderIntent | None,
    *,
    is_stale: bool,
    feed_degraded: bool = False,
) -> TradeGateResult:
    """
    Default: NO_TRADE. Authorize ENTER_LIMIT_* / PASSIVE_QUOTE only if all checks pass.
    Strategy selection does not imply execution.
    """
    threshold_net = float(settings.min_net_edge)
    passive = sel.strategy_id == "passive_market_making"
    exec_q = float(ctx.live.response_score)
    conf = float(fv.confidence) if fv is not None else 0.0
    sp_bps = ctx.live.spread_bps
    depth = float(ctx.live.depth_top_usd or 0.0)

    def _fail(
        reason: NoTradeReason,
        *,
        eg: float | None = None,
        en: float | None = None,
        fp: float | None = None,
        mp: float | None = None,
        ec: float | None = None,
        exec_pass: bool = False,
    ) -> TradeGateResult:
        return TradeGateResult(
            trade_allowed=False,
            recommended_action=OperationalAction.NO_TRADE,
            reason=reason.value,
            edge_gross=eg,
            edge_net=en,
            fair_prob=fp,
            market_prob=mp,
            estimated_cost=ec,
            confidence=conf,
            execution_quality=exec_q,
            threshold_net=threshold_net,
            risk_passed=True,
            execution_passed=exec_pass,
            passive_quote=passive,
        )

    if feed_degraded:
        return _fail(NoTradeReason.FEED_DEGRADED, fp=fv.fair_prob if fv else None, mp=fv.market_prob if fv else None)

    if is_stale:
        return _fail(NoTradeReason.MARKET_STALE, fp=fv.fair_prob if fv else None, mp=fv.market_prob if fv else None)

    if sel.strategy_id == "no_trade":
        return _fail(NoTradeReason.STRATEGY_NOT_APPLICABLE)

    if fv is None:
        return _fail(NoTradeReason.STRATEGY_NOT_APPLICABLE)

    fp = float(fv.fair_prob)
    mp = float(fv.market_prob)
    ec = float(fv.estimated_cost)

    if intent is None:
        return _fail(
            NoTradeReason.NO_INTENT,
            fp=fp,
            mp=mp,
            ec=ec,
            eg=float(fv.edge_gross),
            en=float(fv.edge_net),
        )

    eg = float(fv.directional_edge_gross(intent.side))
    en = float(fv.directional_edge_net(intent.side))

    if sp_bps is None or float(sp_bps) > float(settings.trade_gate_max_spread_bps):
        return _fail(
            NoTradeReason.SPREAD_TOO_WIDE,
            eg=eg,
            en=en,
            fp=fp,
            mp=mp,
            ec=ec,
            exec_pass=exec_q >= float(settings.min_execution_quality),
        )

    if depth < float(settings.min_depth_usd_trade):
        return _fail(
            NoTradeReason.DEPTH_TOO_LOW,
            eg=eg,
            en=en,
            fp=fp,
            mp=mp,
            ec=ec,
        )

    if conf < float(settings.min_trade_confidence):
        return _fail(NoTradeReason.CONFIDENCE_TOO_LOW, eg=eg, en=en, fp=fp, mp=mp, ec=ec)

    if exec_q < float(settings.min_execution_quality):
        return _fail(
            NoTradeReason.EXECUTION_QUALITY_TOO_LOW,
            eg=eg,
            en=en,
            fp=fp,
            mp=mp,
            ec=ec,
            exec_pass=False,
        )

    if eg <= 0.0:
        return _fail(NoTradeReason.EDGE_BELOW_THRESHOLD, eg=eg, en=en, fp=fp, mp=mp, ec=ec)

    if en <= 0.0:
        return _fail(NoTradeReason.EDGE_NET_NEGATIVE, eg=eg, en=en, fp=fp, mp=mp, ec=ec)

    if eg < float(settings.min_gross_edge):
        return _fail(NoTradeReason.EDGE_BELOW_THRESHOLD, eg=eg, en=en, fp=fp, mp=mp, ec=ec)

    if en < float(settings.min_net_edge):
        return _fail(NoTradeReason.EDGE_BELOW_THRESHOLD, eg=eg, en=en, fp=fp, mp=mp, ec=ec)

    if passive:
        action = OperationalAction.PASSIVE_QUOTE
    elif intent.side == OrderSide.BUY:
        action = OperationalAction.ENTER_LIMIT_BUY
    else:
        action = OperationalAction.ENTER_LIMIT_SELL

    return TradeGateResult(
        trade_allowed=True,
        recommended_action=action,
        reason="authorized",
        edge_gross=eg,
        edge_net=en,
        fair_prob=fp,
        market_prob=mp,
        estimated_cost=ec,
        confidence=conf,
        execution_quality=exec_q,
        threshold_net=threshold_net,
        risk_passed=True,
        execution_passed=True,
        passive_quote=passive,
    )
