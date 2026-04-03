"""Execution: pre-trade, dedup, slippage guard, depth check, paper vs live."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from app.clients.clob_client import ClobWrapper
from app.config import RunMode, Settings
from app.logger import get_logger
from app.models.order import OrderIntent, OrderSide, TimeInForce
from app.models.orderbook import OrderBookSnapshot
from app.models.risk import RejectReason
from app.paper.paper_broker import PaperBroker
from app.risk.risk_engine import RiskEngine
from app.services.persistence_service import PersistenceService
from app.services.portfolio_service import PortfolioService
from app.utils.ids import stable_hash

if TYPE_CHECKING:
    from app.execution.quote_engine import QuoteEngine
    from app.execution.reconciliation import ReconciliationService
    from app.monitor.advanced_metrics import AdvancedMetrics

log = get_logger("execution")


class ExecutionResult:
    def __init__(
        self,
        ok: bool,
        *,
        reason: RejectReason = RejectReason.OK,
        message: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.ok = ok
        self.reason = reason
        self.message = message
        self.payload = payload or {}


class ExecutionService:
    """Limit orders only; delegates fills to PaperBroker or CLOB."""

    def __init__(
        self,
        settings: Settings,
        risk: RiskEngine,
        clob: ClobWrapper,
        paper: PaperBroker,
        portfolio: PortfolioService,
        persistence: PersistenceService,
        *,
        quote_engine: QuoteEngine | None = None,
        metrics: AdvancedMetrics | None = None,
        reconciliation: ReconciliationService | None = None,
    ) -> None:
        self._settings = settings
        self._risk = risk
        self._clob = clob
        self._paper = paper
        self._portfolio = portfolio
        self._persistence = persistence
        self._quote = quote_engine
        self._metrics = metrics
        self._recon = reconciliation
        self._recent_keys: dict[str, float] = {}
        self._dedup_ttl = 60.0

    def _prune_dedup(self) -> None:
        now = time.time()
        self._recent_keys = {k: t for k, t in self._recent_keys.items() if now - t < self._dedup_ttl}

    def _dedup_key(self, intent: OrderIntent) -> str:
        return stable_hash(
            (
                intent.token_id,
                intent.side.value,
                f"{intent.price:.6f}",
                f"{intent.size:.6f}",
                intent.tif.value,
            )
        )

    def slippage_ok(self, intent: OrderIntent, book: OrderBookSnapshot) -> bool:
        mid = book.mid()
        if mid is None or mid <= 0:
            return False
        if intent.side == OrderSide.BUY:
            ref = book.best_ask or mid
            slip_bps = abs((intent.price - ref) / mid) * 10000.0
        else:
            ref = book.best_bid or mid
            slip_bps = abs((intent.price - ref) / mid) * 10000.0
        return slip_bps <= self._settings.max_slippage_bps

    def submit(
        self,
        intent: OrderIntent,
        *,
        mode: RunMode,
        book: OrderBookSnapshot | None,
        bankroll_usd: float,
        confidence: float,
        edge_net: float | None = None,
        use_maker_quote: bool = False,
        market_id: str = "",
        strategy_id: str = "",
    ) -> ExecutionResult:
        self._prune_dedup()
        key = self._dedup_key(intent)
        if self._recon:
            self._recon.record_intent(
                key,
                {
                    "market_id": market_id or intent.market_id,
                    "strategy_id": strategy_id,
                    "intent": intent.model_dump(),
                    "edge_net": edge_net,
                },
            )

        if key in self._recent_keys:
            self._persistence.insert_risk_event("duplicate_order", key)
            return ExecutionResult(False, reason=RejectReason.DUPLICATE_ORDER, message="dedup")

        if self._quote and (use_maker_quote or self._settings.maker_first_post_only):
            en = edge_net if edge_net is not None else 0.03
            adj = self._quote.prepare_intent(intent, edge_net=float(en))
            if adj is None:
                return ExecutionResult(False, reason=RejectReason.OTHER, message="quote_low_edge")
            intent = adj

        notional = abs(intent.price * intent.size)
        is_adding_to_loser = False
        pos = self._portfolio.get(intent.market_id, intent.token_id)
        if pos and intent.side == OrderSide.BUY and pos.size < 0:
            is_adding_to_loser = True
        if pos and intent.side == OrderSide.SELL and pos.size > 0:
            is_adding_to_loser = True

        rc = self._risk.check_pre_trade(
            intent,
            mode=mode,
            book=book,
            notional_usd=notional,
            is_adding_to_loser=is_adding_to_loser,
        )
        if not rc.allowed:
            log.info("order_rejected", reason=rc.reason.value, message=rc.message)
            self._persistence.insert_risk_event(rc.reason.value, rc.message, {"market_id": intent.market_id})
            return ExecutionResult(False, reason=rc.reason, message=rc.message)

        if book and not self.slippage_ok(intent, book):
            return ExecutionResult(False, reason=RejectReason.SLIPPAGE, message="slippage")

        if mode in (RunMode.PAPER, RunMode.DRY_RUN):
            if mode == RunMode.DRY_RUN:
                log.info("dry_run_skip_submit", intent=intent.model_dump())
                return ExecutionResult(True, message="dry_run")
            fill = self._paper.simulate_fill(intent, book)
            self._recent_keys[key] = time.time()
            oid = fill.get("order_id", "paper")
            self._persistence.insert_order(oid, {**intent.model_dump(), "status": "filled", "mode": "paper"})
            fp = float(fill.get("fill_price", intent.price))
            sz = float(fill.get("fill_size", intent.size))
            notion = abs(fp * sz)
            self._risk.state.exposure.per_market[intent.market_id] = (
                self._risk.state.exposure.per_market.get(intent.market_id, 0.0) + notion
            )
            self._risk.state.exposure.total += notion
            if self._metrics:
                self._metrics.record_order_submitted()
                if edge_net is not None:
                    self._metrics.record_edge_at_entry(edge_net)
                self._metrics.record_fill(maker=True)
            if self._recon:
                self._recon.record_sent(key, {"orderID": oid, "id": oid, "status": "filled", "mode": "paper"})
            return ExecutionResult(True, payload=fill)

        if mode == RunMode.LIVE:
            if not self._settings.enable_live_trading:
                return ExecutionResult(False, reason=RejectReason.LIVE_DISABLED)
            post_only = bool(self._settings.maker_first_post_only)
            try:
                resp = self._clob.create_limit_order_post(intent, post_only=post_only)
                self._risk.register_api_success()
                self._recent_keys[key] = time.time()
                oid = str(resp.get("orderID") or resp.get("id") or "unknown")
                self._persistence.insert_order(oid, {**intent.model_dump(), "status": "open", "mode": "live", "resp": resp})
                if self._metrics:
                    self._metrics.record_order_submitted()
                    if edge_net is not None:
                        self._metrics.record_edge_at_entry(edge_net)
                if self._recon:
                    self._recon.record_sent(key, resp)
                return ExecutionResult(True, payload={"response": resp})
            except Exception as e:
                self._risk.register_api_error()
                log.exception("live_order_failed")
                return ExecutionResult(False, reason=RejectReason.OTHER, message=str(e))

        return ExecutionResult(False, message="unknown_mode")
