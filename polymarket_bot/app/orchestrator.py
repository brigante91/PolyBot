"""Multi-market adaptive engine — universe → filter → analyze → score → select → risk → route."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.analysis.fair_value_engine import FairValueEngine, FairValueInputs
from app.analysis.historical_analyzer import HistoricalAnalyzer
from app.analysis.live_market_analyzer import LiveMarketAnalyzer
from app.analysis.market_scorer import MarketScorer
from app.clients.polymarket_rest import PolymarketRestFacade
from app.config import RunMode, Settings
from app.data.market_store import MarketStateStore
from app.discovery.market_filter import MarketFilter
from app.discovery.market_universe import MarketUniverseScanner
from app.execution.order_router import OrderRouter, RoutedIntent
from app.execution.reconciliation import ReconciliationService
from app.execution.ws_handler import WsMarketHub
from app.v3_coordinator import V3Coordinator
from app.logger import get_logger
from app.models.context import MarketContext
from app.models.decision import MarketDecisionRecord, OperationalAction
from app.models.order import OrderSide
from app.monitor.metrics import OrchestratorMetrics
from app.paper.paper_broker import PaperBroker
from app.portfolio.exposure_allocator import ExposureAllocator
from app.portfolio.portfolio_manager import PortfolioManager
from app.portfolio.pnl_tracker import PnLTracker
from app.portfolio.position_registry import PositionRegistry
from app.risk.portfolio_risk_rules import check_portfolio
from app.risk.risk_engine import RiskEngine
from app.services.execution_service import ExecutionService
from app.services.persistence_service import PersistenceService
from app.services.portfolio_service import PortfolioService
from app.state.runtime_state import runtime_state
from app.strategy.strategy_selector import StrategySelector

log = get_logger("orchestrator")


class MultiMarketOrchestrator:
    """Central coordinator — preserves existing execution/risk/paper by composition."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.facade = PolymarketRestFacade(settings)
        self.scanner = MarketUniverseScanner(settings, self.facade.gamma)
        self.market_filter = MarketFilter(settings)
        self.ws_hub: WsMarketHub | None = WsMarketHub() if settings.enable_ws else None
        self.live_analyzer = LiveMarketAnalyzer(
            settings,
            self.facade.clob,
            ws_hub=self.ws_hub,
        )
        self.historical = HistoricalAnalyzer()
        self.scorer = MarketScorer(settings)
        self.selector = StrategySelector(settings)
        self.risk = RiskEngine(settings)
        self.registry = PositionRegistry()
        self.pnl = PnLTracker()
        self.portfolio = PortfolioManager(settings, self.risk, self.registry, self.pnl)
        self.store = MarketStateStore()
        self.persistence = PersistenceService(settings)
        self.paper = PaperBroker(settings)
        self.portfolio_legacy = PortfolioService()
        self.execution = ExecutionService(
            settings,
            self.risk,
            self.facade.clob,
            self.paper,
            self.portfolio_legacy,
            self.persistence,
        )
        self.router = OrderRouter(settings, self.execution)
        self.recon = ReconciliationService(self.persistence)
        self._v3: V3Coordinator | None = None
        self._v3_ws_started = False
        if settings.enable_ws and self.ws_hub is not None:
            self._v3 = V3Coordinator(settings, self.ws_hub, self.recon)
        self.allocator = ExposureAllocator(settings, self.risk)
        self.metrics = OrchestratorMetrics()
        self._fve = FairValueEngine(fee_bps=settings.paper_fee_bps, slippage_bps=settings.paper_slippage_bps)

    def close(self) -> None:
        if self._v3 is not None:
            self._v3.stop()
        self.facade.close()

    def run_cycle(self, mode: RunMode) -> OrchestratorMetrics:
        self.metrics = OrchestratorMetrics()
        self.risk.reset_intraday_if_needed()

        universe = self.scanner.scan()
        self.metrics.scanned = len(universe)
        filtered, rejected = self.market_filter.filter(universe)
        self.metrics.filtered_out = len(rejected)
        for mid, reason in rejected[:50]:
            log.info("market_rejected", market_id=mid, reason=reason)

        # Pre-sort by liquidity for live REST budget
        filtered.sort(key=lambda c: -(c.liquidity or 0.0))
        top = filtered[: self.settings.live_analysis_top_n]

        if self._v3 is not None and not self._v3_ws_started:
            asset_ids: list[str] = []
            condition_ids: list[str] = []
            for c in top:
                tid = c.primary_token_id()
                if tid:
                    asset_ids.append(tid)
                cid = c.condition_id()
                if cid:
                    condition_ids.append(cid)
            asset_ids = list(dict.fromkeys(asset_ids))
            condition_ids = list(dict.fromkeys(condition_ids))
            if asset_ids:
                self._v3.start_market(asset_ids)
            if condition_ids:
                self._v3.start_user(condition_ids)
            self._v3_ws_started = True

        contexts: list[MarketContext] = []
        for c in top:
            live = self.live_analyzer.analyze(c)
            hist = self.historical.profile(c)
            scores = self.scorer.score(c, live, hist)
            ctx = MarketContext(
                candidate=c,
                live=live,
                historical=hist,
                score_total=float(scores["score_total"]),
            )
            contexts.append(ctx)
            self.metrics.live_analyzed += 1

        contexts.sort(key=lambda x: -x.score_total)
        self.metrics.ranked = len(contexts)

        tui_markets: list[dict[str, Any]] = []
        for ctx in contexts[:18]:
            mid = ctx.live.book.mid() if ctx.live.book else 0.5
            ttr_y = 1e-6
            if ctx.candidate.end_date:
                now = datetime.now(timezone.utc)
                end = ctx.candidate.end_date
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                ttr_y = max(1e-10, (end - now).total_seconds() / (365.25 * 86400.0))
            fv = self._fve.estimate(
                FairValueInputs(
                    market_mid=float(mid or 0.5),
                    underlying_price=None,
                    price_to_beat=None,
                    time_to_expiry_years=ttr_y,
                    price_velocity=ctx.live.mid_change_1m_bps / 10000.0,
                    volatility_annual=0.55,
                    book_imbalance=ctx.live.book_imbalance,
                    distance_from_mid_bps=0.0,
                )
            )
            sel = self.selector.select(ctx)
            tui_markets.append(
                {
                    "id": ctx.candidate.market_id,
                    "score": round(ctx.score_total, 3),
                    "strategy": sel.strategy_id,
                    "edge": round(fv.edge_net, 4),
                    "fair": round(fv.fair_prob, 3),
                    "mkt": round(fv.market_prob, 3),
                }
            )
        lat = "—"
        if self.settings.enable_ws and self._v3 is not None:
            lm = self._v3.market_latency_ms
            lat = f"{int(lm)}" if lm is not None else "—"
        ws_status = "REST"
        if self.settings.enable_ws:
            if self.ws_hub and self.ws_hub.stats().get("last_event_at"):
                ws_status = "OK"
            else:
                ws_status = "ON"

        runtime_state.update(
            markets=tui_markets,
            portfolio={
                "exposure_pct": round(
                    100.0 * self.risk.state.exposure.total / max(self.settings.max_total_exposure_usd, 1.0),
                    1,
                ),
                "daily_pnl_pct": 0.0,
                "open_positions": self.risk.state.open_position_count,
            },
            system={
                "ws": ws_status,
                "latency_ms": lat,
                "health": "GOOD" if self.risk.state.consecutive_api_errors < 3 else "DEGRADED",
            },
        )

        routed: list[RoutedIntent] = []
        for rank, ctx in enumerate(contexts, start=1):
            ctx = ctx.model_copy(update={"rank": rank})
            scores = self.scorer.score(ctx.candidate, ctx.live, ctx.historical)
            if not scores.get("recommended", False):
                self.metrics.no_trade += 1
                log.info(
                    "decision_skip_low_score",
                    market_id=ctx.candidate.market_id,
                    score_total=ctx.score_total,
                )
                continue

            sel = self.selector.select(ctx)
            edge = abs(ctx.live.mid_change_1m_bps) / 10000.0
            rec = MarketDecisionRecord(
                market_id=ctx.candidate.market_id,
                tradable=True,
                rank=rank,
                selected_strategy=sel.strategy_id,
                confidence=sel.confidence,
                edge_estimate=edge,
                execution_quality=float(ctx.live.response_score),
                recommended_action=sel.action,
                recommended_size_usd=0.0,
                reason=sel.rationale,
            )

            if sel.strategy_id == "no_trade" or sel.action == OperationalAction.NO_TRADE:
                self.metrics.no_trade += 1
                self.store.update_decision(
                    ctx.candidate.market_id,
                    strategy=sel.strategy_id,
                    score=ctx.score_total,
                    action=OperationalAction.NO_TRADE,
                    reason=sel.rationale,
                )
                log.info("decision", **rec.model_dump())
                continue

            if not self.portfolio.can_open_more():
                self.metrics.no_trade += 1
                rec.reason = "max_concurrent_positions"
                log.info("decision", **rec.model_dump())
                continue

            intent = self.selector.build_intent(ctx, sel.strategy_id)
            if intent is None:
                self.metrics.no_trade += 1
                continue

            usd = self.allocator.recommend_usd(ctx, sel.confidence)
            px = float(intent.price)
            intent = intent.model_copy(update={"size": max(usd / max(px, 1e-9), 0.0)})

            pr = check_portfolio(
                self.risk,
                positions_after=self.portfolio.open_positions_count() + 1,
                group_exposure_usd=0.0,
                strategy_id=sel.strategy_id,
                category=ctx.candidate.category,
            )
            if not pr.allowed:
                self.metrics.rejected_risk += 1
                rec.reason = pr.message
                log.info("portfolio_block", **rec.model_dump())
                continue

            action = OperationalAction.ENTER_LIMIT_BUY
            if intent.side == OrderSide.SELL:
                action = OperationalAction.ENTER_LIMIT_SELL
            if sel.action == OperationalAction.PASSIVE_QUOTE:
                action = OperationalAction.PASSIVE_QUOTE

            rec = rec.model_copy(
                update={
                    "recommended_action": action,
                    "recommended_size_usd": usd,
                    "tradable": True,
                }
            )
            log.info("decision", **rec.model_dump())

            priority = ctx.score_total * sel.confidence
            routed.append(
                RoutedIntent(
                    priority=priority,
                    market_id=ctx.candidate.market_id,
                    intent=intent,
                    book=ctx.live.book,
                    strategy_id=sel.strategy_id,
                    confidence=sel.confidence,
                )
            )

        bankroll = max(self.settings.max_total_exposure_usd, 1000.0)
        results = self.router.route_batch(routed, mode=mode, bankroll_usd=bankroll)
        self.metrics.routed = len(results)

        for ri, er in results:
            self.recon.record_execution(market_id=ri.market_id, strategy_id=ri.strategy_id, res=er)
            if er.ok and mode != RunMode.DRY_RUN:
                self.risk.state.open_position_count = min(
                    self.settings.max_concurrent_positions,
                    self.risk.state.open_position_count + 1,
                )

        self.persistence.heartbeat({"orchestrator": self.metrics.to_dict()})
        runtime_state.push_debug(
            f"cycle scanned={self.metrics.scanned} routed={self.metrics.routed} no_trade={self.metrics.no_trade}"
        )
        return self.metrics
