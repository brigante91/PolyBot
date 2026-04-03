"""Multi-market adaptive engine — universe → filter → analyze → score → select → risk → route."""

from __future__ import annotations

import time
from typing import Any

from app.analysis.fair_value_engine import FairValueEngine
from app.analysis.historical_analyzer import HistoricalAnalyzer
from app.analysis.live_market_analyzer import LiveMarketAnalyzer
from app.analysis.market_scorer import MarketScorer
from app.clients.polymarket_rest import PolymarketRestFacade
from app.clients.spot_price_client import SpotPriceClient
from app.config import RunMode, Settings
from app.decision import evaluate_trade_gate
from app.decision.trade_gate import NoTradeReason
from app.data.market_store import MarketStateStore
from app.discovery.market_filter import MarketFilter
from app.discovery.market_universe import MarketUniverseScanner
from app.execution.order_router import OrderRouter, RoutedIntent
from app.execution.quote_engine import QuoteEngine
from app.execution.reconciliation import ReconciliationService
from app.execution.ws_handler import WsMarketHub
from app.data.session_recorder import SessionRecorder
from app.monitor.advanced_metrics import AdvancedMetrics
from app.portfolio.correlation_manager import CorrelationManager
from app.realtime.state_engine import RealtimeStateEngine
from app.v3_coordinator import V3Coordinator
from app.logger import get_logger
from app.models.candidate import CandidateMarket
from app.models.context import MarketContext
from app.models.decision import MarketDecisionRecord, OperationalAction
from app.monitor.metrics import OrchestratorMetrics
from app.paper.paper_broker import PaperBroker
from app.portfolio.exposure_allocator import ExposureAllocator
from app.portfolio.portfolio_manager import PortfolioManager
from app.portfolio.pnl_tracker import PnLTracker
from app.portfolio.position_registry import PositionRegistry
from app.risk.kill_switch import KillSwitch
from app.risk.portfolio_risk_rules import check_portfolio
from app.risk.risk_engine import RiskEngine
from app.services.execution_service import ExecutionService
from app.services.persistence_service import PersistenceService
from app.services.portfolio_service import PortfolioService
from app.state.runtime_projection import project_cycle
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
        self.adv_metrics = AdvancedMetrics()
        self.recon = ReconciliationService(self.persistence, metrics=self.adv_metrics)
        self.quote_engine = QuoteEngine(settings, self.facade.clob)
        self.execution = ExecutionService(
            settings,
            self.risk,
            self.facade.clob,
            self.paper,
            self.portfolio_legacy,
            self.persistence,
            quote_engine=self.quote_engine,
            metrics=self.adv_metrics,
            reconciliation=self.recon,
        )
        self.router = OrderRouter(settings, self.execution)
        self._corr = CorrelationManager(settings)
        self._rt_state: RealtimeStateEngine | None = RealtimeStateEngine() if settings.enable_ws else None
        self._v3: V3Coordinator | None = None
        self._v3_ws_started = False
        if settings.enable_ws and self.ws_hub is not None:
            self._v3 = V3Coordinator(settings, self.ws_hub, self.recon, state_engine=self._rt_state)
        self._recorder = SessionRecorder()
        self._recorder.open_default()
        self.allocator = ExposureAllocator(settings, self.risk)
        self.metrics = OrchestratorMetrics()
        self._fve = FairValueEngine(fee_bps=settings.paper_fee_bps, slippage_bps=settings.paper_slippage_bps)
        self._spot = SpotPriceClient(settings)
        self._spot_cache: dict[str, tuple[float, float]] = {}
        log.info(
            "trade_gate_settings",
            min_gross_edge=settings.min_gross_edge,
            min_net_edge=settings.min_net_edge,
            min_confidence=settings.min_trade_confidence,
            min_execution_quality=settings.min_execution_quality,
            trade_gate_max_spread_bps=settings.trade_gate_max_spread_bps,
            min_depth_usd_trade=settings.min_depth_usd_trade,
        )

    def close(self) -> None:
        if self._v3 is not None:
            self._v3.stop()
        self._recorder.close()
        self._spot.close()
        self.facade.close()

    def _underlying_for_candidate(self, c: CandidateMarket) -> tuple[float | None, float | None]:
        """REST spot for crypto keywords; RTDS can populate the same tuple later."""
        sym = c.infer_spot_symbol()
        if not sym or not self.settings.enable_spot_price_rest:
            return None, None
        now = time.time()
        cached = self._spot_cache.get(sym)
        if cached and now - cached[1] < self.settings.spot_price_ttl_seconds:
            return cached[0], None
        px = self._spot.fetch_usd(sym)
        if px is not None:
            self._spot_cache[sym] = (px, now)
        return px, None

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

        enriched: list[MarketContext] = []
        for ctx in contexts:
            u, k = self._underlying_for_candidate(ctx.candidate)
            fv = ctx.compute_fair_value(self._fve, underlying_price=u, price_to_beat=k)
            enriched.append(ctx.model_copy(update={"fair_value": fv}))
        contexts = enriched

        ks = KillSwitch(self.settings).is_active()
        user_ws_degraded = bool(
            self._rt_state
            and mode == RunMode.LIVE
            and self._rt_state.is_user_feed_degraded(self.settings)
        )

        tui_markets: list[dict[str, Any]] = []
        decision_trace: list[dict[str, Any]] = []
        for ctx in contexts[:18]:
            fv = ctx.fair_value
            scores_row = self.scorer.score(ctx.candidate, ctx.live, ctx.historical)
            sel = self.selector.select(ctx)
            tid = ctx.candidate.primary_token_id() or ""
            stale = bool(self._rt_state.is_stale(tid)) if self._rt_state and tid else False
            blocked = not scores_row.get("recommended", False)
            intent = (
                self.selector.build_intent(ctx, sel.strategy_id)
                if sel.strategy_id != "no_trade"
                else None
            )
            gate = evaluate_trade_gate(
                self.settings,
                ctx,
                fv,
                sel,
                intent,
                is_stale=stale,
                feed_degraded=user_ws_degraded,
            )
            eg = gate.edge_net
            row = {
                "id": ctx.candidate.market_id,
                "score": round(ctx.score_total, 3),
                "strategy": sel.strategy_id,
                "confidence": round(sel.confidence, 3),
                "second_strategy": sel.second_best_id or "—",
                "edge_gross": round(gate.edge_gross, 6) if gate.edge_gross is not None else None,
                "edge": round(eg, 6) if eg is not None else None,
                "edge_net": round(eg, 6) if eg is not None else None,
                "fair": round(gate.fair_prob, 6) if gate.fair_prob is not None else None,
                "mkt": round(gate.market_prob, 6) if gate.market_prob is not None else None,
                "threshold_net": gate.threshold_net,
                "trade_allowed": gate.trade_allowed,
                "action": gate.recommended_action.value,
                "reason": gate.reason,
                "explain": (sel.explain_selected or "")[:100],
                "tradable": bool(scores_row.get("recommended", False)),
                "token_id": tid[:14],
                "stale": stale,
                "blocked": blocked,
                "row_tier": (
                    "green"
                    if gate.trade_allowed
                    else ("yellow" if sel.strategy_id != "no_trade" else "red")
                ),
            }
            if stale or gate.reason in ("feed_degraded", "market_stale"):
                row["row_tier"] = "red"
            tui_markets.append(row)
            decision_trace.append(
                {
                    "market_id": ctx.candidate.market_id[:14],
                    "strategy": sel.strategy_id,
                    "second": sel.second_best_id or "—",
                    "conf": round(sel.confidence, 6),
                    "edge_net": round(eg, 6) if eg is not None else None,
                    "edge_gross": round(gate.edge_gross, 6) if gate.edge_gross is not None else None,
                    "fair": round(gate.fair_prob, 6) if gate.fair_prob is not None else None,
                    "mkt": round(gate.market_prob, 6) if gate.market_prob is not None else None,
                    "threshold_net": gate.threshold_net,
                    "trade_allowed": gate.trade_allowed,
                    "action": gate.recommended_action.value,
                    "final_reason": gate.reason,
                    "explain": (sel.explain_selected or "")[:90],
                    "scorer_ok": bool(scores_row.get("recommended", False)),
                    "rationale": (sel.rationale or "")[:100],
                    "risk_gate": "ok",
                    "risk_passed": True,
                    "execution_passed": gate.execution_passed,
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

        risk_limits: dict[str, Any] = {
            "max_order_usd": self.settings.max_order_size_usd,
            "max_total_exposure_usd": self.settings.max_total_exposure_usd,
            "max_group_exposure_usd": self.settings.max_exposure_group_usd,
            "daily_loss_limit_usd": self.settings.daily_loss_limit_usd,
            "max_open_orders": self.settings.max_open_orders,
        }

        exec_gate = "OK"
        if ks:
            exec_gate = "KILL_SWITCH"
        elif runtime_state.paused:
            exec_gate = "PAUSED"
        elif runtime_state.soft_kill:
            exec_gate = "SOFT_KILL"
        elif user_ws_degraded:
            exec_gate = "USER_WS_DEGRADED"

        positions_rows: list[dict[str, Any]] = [
            {
                "market_id": k[:14],
                "side": "—",
                "size_usd": round(v, 2),
                "avg_entry": "—",
                "unreal_pnl": "—",
                "real_pnl": "—",
            }
            for k, v in self.risk.state.exposure.per_market.items()
            if abs(v) > 1e-6
        ][:24]

        portfolio_snap = {
            "exposure_pct": round(
                100.0 * self.risk.state.exposure.total / max(self.settings.max_total_exposure_usd, 1.0),
                1,
            ),
            "capital_used_pct": round(
                100.0 * self.risk.state.exposure.total / max(self.settings.max_total_exposure_usd, 1.0),
                1,
            ),
            "daily_pnl_pct": 0.0,
            "open_positions": self.risk.state.open_position_count,
            "per_market_usd": {k[:14]: round(v, 2) for k, v in self.risk.state.exposure.per_market.items()},
        }

        system_snap: dict[str, Any] = {
            "ws": ws_status,
            "latency_ms": lat,
            "health": "GOOD" if self.risk.state.consecutive_api_errors < 3 else "DEGRADED",
            "kill_switch": ks,
            "paused": runtime_state.paused,
            "soft_kill": runtime_state.soft_kill,
            "execution_gate": exec_gate,
            "user_ws_degraded": user_ws_degraded,
            "trade_gate": {
                "min_gross_edge": self.settings.min_gross_edge,
                "min_net_edge": self.settings.min_net_edge,
                "min_confidence": self.settings.min_trade_confidence,
                "min_execution_quality": self.settings.min_execution_quality,
                "max_spread_bps": self.settings.trade_gate_max_spread_bps,
                "min_depth_usd": self.settings.min_depth_usd_trade,
            },
        }

        project_cycle(
            markets=tui_markets,
            decisions=decision_trace,
            orders=[],
            portfolio=portfolio_snap,
            system=system_snap,
            metrics=self.adv_metrics.to_dict(),
            risk_limits=risk_limits,
            rt_engine=self._rt_state,
            recon=self.recon,
            positions=positions_rows,
            trades=None,
            runtime_mode=mode.value,
            ui_mode="run",
        )

        routed: list[RoutedIntent] = []
        if ks or runtime_state.paused or runtime_state.soft_kill or user_ws_degraded:
            reason = (
                "kill_switch"
                if ks
                else (
                    "paused"
                    if runtime_state.paused
                    else ("soft_kill" if runtime_state.soft_kill else "user_ws_degraded")
                )
            )
            runtime_state.push_debug(f"execution skipped ({reason})")
            self.persistence.heartbeat({"orchestrator": self.metrics.to_dict(), "skipped": reason})
            runtime_state.push_debug(
                f"cycle scanned={self.metrics.scanned} routed=0 skipped={reason}"
            )
            rt_full = self._rt_state.snapshot() if self._rt_state else {}
            self._recorder.record(
                "cycle",
                {
                    "schema_version": 1,
                    "mode": mode.value,
                    "markets": tui_markets,
                    "decisions": decision_trace,
                    "orders": [],
                    "metrics": self.adv_metrics.to_dict(),
                    "risk": {**risk_limits, "reconciliation": self.recon.snapshot(), "realtime_engine": rt_full},
                    "skipped": reason,
                },
            )
            return self.metrics

        for rank, ctx in enumerate(contexts, start=1):
            ctx = ctx.model_copy(update={"rank": rank})
            scores = self.scorer.score(ctx.candidate, ctx.live, ctx.historical)
            if not scores.get("recommended", False):
                self.metrics.no_trade += 1
                runtime_state.push_no_trade(ctx.candidate.market_id, "low_score")
                log.info(
                    "decision_skip_low_score",
                    market_id=ctx.candidate.market_id,
                    score_total=ctx.score_total,
                )
                continue

            sel = self.selector.select(ctx)
            fv = ctx.fair_value
            tid = ctx.candidate.primary_token_id() or ""
            stale = bool(self._rt_state.is_stale(tid)) if self._rt_state and tid else False
            intent = (
                self.selector.build_intent(ctx, sel.strategy_id)
                if sel.strategy_id != "no_trade"
                else None
            )
            gate = evaluate_trade_gate(
                self.settings,
                ctx,
                fv,
                sel,
                intent,
                is_stale=stale,
                feed_degraded=False,
            )

            en_val = gate.edge_net
            rec = MarketDecisionRecord(
                market_id=ctx.candidate.market_id,
                tradable=True,
                rank=rank,
                selected_strategy=sel.strategy_id,
                second_best_strategy=sel.second_best_id or "",
                confidence=round(sel.confidence, 6),
                fair_prob=round(gate.fair_prob, 6) if gate.fair_prob is not None else None,
                market_prob=round(gate.market_prob, 6) if gate.market_prob is not None else None,
                edge_gross=round(gate.edge_gross, 6) if gate.edge_gross is not None else None,
                estimated_cost=round(gate.estimated_cost, 6) if gate.estimated_cost is not None else None,
                edge_net=round(en_val, 6) if en_val is not None else None,
                threshold_net=gate.threshold_net,
                edge_estimate=round(en_val, 6) if en_val is not None else 0.0,
                execution_quality=round(gate.execution_quality, 6),
                trade_allowed=gate.trade_allowed,
                recommended_action=gate.recommended_action,
                recommended_size_usd=0.0,
                reason=gate.reason,
                strategy_rationale=sel.rationale,
            )

            self.adv_metrics.record_trade_gate_outcome(
                strategy_selected=(sel.strategy_id != "no_trade"),
                trade_allowed=gate.trade_allowed,
                reason=gate.reason,
                edge_net=en_val,
            )

            if sel.strategy_id == "no_trade":
                self.metrics.no_trade += 1
                log.info("decision", **rec.model_dump())
                runtime_state.push_no_trade(ctx.candidate.market_id, sel.rationale[:40])
                self.store.update_decision(
                    ctx.candidate.market_id,
                    strategy=sel.strategy_id,
                    score=ctx.score_total,
                    action=OperationalAction.NO_TRADE,
                    reason=sel.rationale,
                )
                continue

            if not gate.trade_allowed:
                self.metrics.no_trade += 1
                log.info("decision", **rec.model_dump())
                runtime_state.push_no_trade(ctx.candidate.market_id, gate.reason[:48])
                self.store.update_decision(
                    ctx.candidate.market_id,
                    strategy=sel.strategy_id,
                    score=ctx.score_total,
                    action=OperationalAction.NO_TRADE,
                    reason=gate.reason,
                )
                continue

            if not self.portfolio.can_open_more():
                self.metrics.no_trade += 1
                runtime_state.push_no_trade(ctx.candidate.market_id, "max_positions")
                rec = rec.model_copy(
                    update={
                        "trade_allowed": False,
                        "recommended_action": OperationalAction.NO_TRADE,
                        "reason": "max_concurrent_positions",
                    }
                )
                log.info("decision", **rec.model_dump())
                continue

            usd = (
                self.allocator.recommend_usd(ctx, sel.confidence)
                * max(0.25, min(2.0, runtime_state.risk_level))
            )
            px = float(intent.price)
            intent = intent.model_copy(update={"size": max(usd / max(px, 1e-9), 0.0)})

            grp = self._corr.group_key(
                ctx.candidate.category,
                ctx.candidate.slug,
                ctx.candidate.question,
            )
            group_after = self._corr.current_group_exposure(grp) + usd
            pr = check_portfolio(
                self.risk,
                positions_after=self.portfolio.open_positions_count() + 1,
                group_exposure_usd=group_after,
                strategy_id=sel.strategy_id,
                category=ctx.candidate.category,
            )
            if not pr.allowed:
                self.metrics.rejected_risk += 1
                rec = rec.model_copy(
                    update={
                        "trade_allowed": False,
                        "recommended_action": OperationalAction.NO_TRADE,
                        "reason": NoTradeReason.RISK_BLOCKED.value,
                        "strategy_rationale": pr.message,
                    }
                )
                log.info("decision", **rec.model_dump())
                runtime_state.push_no_trade(ctx.candidate.market_id, pr.message[:40])
                runtime_state.push_risk_reject(ctx.candidate.market_id, pr.message[:80])
                self._recorder.record(
                    "risk_reject",
                    {
                        "schema_version": 1,
                        "market_id": ctx.candidate.market_id,
                        "message": pr.message,
                        "strategy": sel.strategy_id,
                    },
                )
                continue

            action = gate.recommended_action
            rec = rec.model_copy(
                update={
                    "recommended_action": action,
                    "recommended_size_usd": usd,
                    "tradable": True,
                    "trade_allowed": True,
                    "reason": "authorized",
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
                    edge_net=en_val,
                    passive_quote=gate.passive_quote,
                    group_key=grp,
                    trade_allowed=True,
                    recommended_action=action,
                )
            )

        bankroll = max(self.settings.max_total_exposure_usd, 1000.0)
        results = self.router.route_batch(routed, mode=mode, bankroll_usd=bankroll)
        self.metrics.routed = len(results)

        order_rows: list[dict[str, Any]] = []
        for ri, er in results:
            self.recon.record_execution(market_id=ri.market_id, strategy_id=ri.strategy_id, res=er)
            if not er.ok:
                lifecycle = "rejected"
            elif mode == RunMode.DRY_RUN:
                lifecycle = "dry_run"
            elif mode == RunMode.TEST:
                lifecycle = "test"
            elif mode == RunMode.PAPER:
                lifecycle = "filled"
            else:
                lifecycle = "sent"
            order_rows.append(
                {
                    "market_id": ri.market_id[:14],
                    "strategy": ri.strategy_id,
                    "side": ri.intent.side.value,
                    "price": round(float(ri.intent.price), 4),
                    "size": round(float(ri.intent.size), 4),
                    "post_only": bool(self.settings.maker_first_post_only),
                    "ok": er.ok,
                    "reason": er.reason.value if hasattr(er, "reason") else "",
                    "lifecycle": lifecycle,
                }
            )
            if er.ok and mode not in (RunMode.DRY_RUN, RunMode.TEST):
                self.risk.state.open_position_count = min(
                    self.settings.max_concurrent_positions,
                    self.risk.state.open_position_count + 1,
                )
                notion = abs(float(ri.intent.price) * float(ri.intent.size))
                self._corr.add_exposure(ri.group_key, notion)

        self.adv_metrics.update_no_trade_ratio(
            self.metrics.no_trade,
            max(1, self.metrics.no_trade + self.metrics.routed + self.metrics.rejected_risk),
        )
        recon_rows = self.recon.recent_lifecycle_rows(limit=20)
        merged_orders = order_rows + recon_rows
        project_cycle(
            markets=tui_markets,
            decisions=decision_trace,
            orders=merged_orders,
            portfolio=portfolio_snap,
            system=system_snap,
            metrics=self.adv_metrics.to_dict(),
            risk_limits=risk_limits,
            rt_engine=self._rt_state,
            recon=self.recon,
            positions=positions_rows,
            trades=None,
            runtime_mode=mode.value,
            ui_mode="run",
        )

        self.persistence.heartbeat({"orchestrator": self.metrics.to_dict()})
        runtime_state.push_debug(
            f"cycle scanned={self.metrics.scanned} routed={self.metrics.routed} no_trade={self.metrics.no_trade}"
        )
        rt_full = self._rt_state.snapshot() if self._rt_state else {}
        self._recorder.record(
            "cycle",
            {
                "schema_version": 1,
                "mode": mode.value,
                "markets": tui_markets,
                "decisions": decision_trace,
                "orders": order_rows,
                "metrics": self.adv_metrics.to_dict(),
                "risk": {**risk_limits, "reconciliation": self.recon.snapshot(), "realtime_engine": rt_full},
            },
        )
        self._recorder.record(
            "ws_health",
            {"schema_version": 1, "feeds": rt_full.get("feeds", {}), "mode": mode.value},
        )
        return self.metrics
