"""Orchestrates discovery, strategy, risk, execution — no CLI concerns."""

from __future__ import annotations

import signal
import time
from typing import Any

from app.clients.clob_client import ClobWrapper
from app.clients.gamma_client import GammaClient
from app.config import RunMode, Settings, load_settings
from app.logger import get_logger
from app.models.order import OrderIntent, OrderSide, TimeInForce
from app.models.signal import SignalAction
from app.paper.paper_broker import PaperBroker
from app.risk.risk_engine import RiskEngine
from app.services.execution_service import ExecutionService
from app.services.market_discovery import MarketDiscoveryService
from app.services.persistence_service import PersistenceService
from app.services.portfolio_service import PortfolioService
from app.strategies import get_strategy

log = get_logger("trading")


class TradingService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.gamma = GammaClient(self.settings)
        self.clob = ClobWrapper(self.settings)
        self.risk = RiskEngine(self.settings)
        self.portfolio = PortfolioService()
        self.persistence = PersistenceService(self.settings)
        self.paper = PaperBroker(self.settings)
        self.execution = ExecutionService(
            self.settings,
            self.risk,
            self.clob,
            self.paper,
            self.portfolio,
            self.persistence,
        )
        self.discovery = MarketDiscoveryService(self.settings, self.gamma)
        self._stop = False

    def shutdown(self) -> None:
        self._stop = True
        self.gamma.close()

    def run_loop(
        self,
        *,
        mode: RunMode | None = None,
        strategy_name: str | None = None,
        max_iterations: int | None = None,
    ) -> None:
        mode = mode or self.settings.mode
        strat_name = strategy_name or self.settings.default_strategy
        strat = get_strategy(strat_name, settings=self.settings)

        def _sig(_a: int, _b: Any) -> None:
            self._stop = True

        signal.signal(signal.SIGINT, _sig)
        signal.signal(signal.SIGTERM, _sig)

        it = 0
        bankroll = max(self.settings.max_total_exposure_usd, 1000.0)

        while not self._stop:
            self.risk.reset_intraday_if_needed()
            self.persistence.heartbeat({"mode": mode.value, "strategy": strat_name})

            markets = self.discovery.discover(max_pages=2)
            if not markets:
                log.warning("no_markets")
                time.sleep(self.settings.heartbeat_interval_seconds)
                continue

            m = markets[0]
            if not m.clob_token_ids:
                time.sleep(5)
                continue
            token_id = m.clob_token_ids[0]
            book = self.clob.get_order_book(token_id)
            mid = self.clob.get_midpoint(token_id)
            spread_bps = book.spread_bps()

            state: dict[str, Any] = {
                "market_id": m.id,
                "token_id": token_id,
                "book": book,
                "mid": mid,
                "spread_bps": spread_bps,
                "depth_usd": self._depth_usd(book),
                "vol_score": 0.2,
                "inventory_imbalance": 0.0,
                "momentum_score": 0.0,
                "volume_confirm": 0.0,
                "late_chase": False,
                "bars_held": 0,
                "implied_prob": float(mid) if mid else None,
                "reference_prob": float(mid) * 0.99 if mid else None,
            }
            strat.prepare({"mid": mid, "book": book})

            if mode == RunMode.DRY_RUN:
                sig = strat.generate_signal(state)
                if sig:
                    self.persistence.insert_signal(sig.model_dump())
                    log.info("dry_run_signal", signal=sig.model_dump())
                it += 1
                if max_iterations and it >= max_iterations:
                    break
                time.sleep(self.settings.heartbeat_interval_seconds)
                continue

            sig = strat.generate_signal(state)
            if not sig:
                it += 1
                if max_iterations and it >= max_iterations:
                    break
                time.sleep(self.settings.heartbeat_interval_seconds)
                continue

            self.persistence.insert_signal(sig.model_dump())

            if sig.action in (SignalAction.QUOTE_BID, SignalAction.QUOTE_ASK, SignalAction.NONE):
                it += 1
                if max_iterations and it >= max_iterations:
                    break
                time.sleep(self.settings.heartbeat_interval_seconds)
                continue

            side = OrderSide.BUY if sig.action == SignalAction.BUY else OrderSide.SELL
            px = float(sig.price or mid or 0.5)
            sz = self.risk.suggest_size(
                bankroll_usd=bankroll,
                confidence=sig.confidence,
                spread_bps=spread_bps,
                mid_price=mid,
            )
            notional = max(sz, 1.0)
            size_shares = notional / max(px, 1e-6)

            intent = OrderIntent(
                market_id=m.id,
                token_id=token_id,
                side=side,
                price=px,
                size=size_shares,
                tif=TimeInForce.GTC,
            )

            res = self.execution.submit(
                intent,
                mode=mode,
                book=book,
                bankroll_usd=bankroll,
                confidence=sig.confidence,
            )
            log.info("submit_result", ok=res.ok, reason=res.reason.value, message=res.message)

            it += 1
            if max_iterations and it >= max_iterations:
                break
            time.sleep(self.settings.heartbeat_interval_seconds)

    @staticmethod
    def _depth_usd(book: Any) -> float:
        mid = book.mid()
        if mid is None or mid <= 0:
            return 0.0
        bid_sz = book.bids[0].size if book.bids else 0.0
        ask_sz = book.asks[0].size if book.asks else 0.0
        return (bid_sz + ask_sz) * mid
