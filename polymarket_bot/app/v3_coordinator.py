"""Optional WS + hub wiring for event-driven market data (enable ENABLE_WS)."""

from __future__ import annotations

from app.clients.polymarket_ws_market import PolymarketWsMarket
from app.clients.polymarket_ws_user import PolymarketWsUser
from app.config import Settings
from app.execution.ws_handler import WsMarketHub
from app.execution.reconciliation import ReconciliationService
from app.logger import get_logger

log = get_logger("v3_coordinator")


class V3Coordinator:
    """Starts market (and optionally user) WebSocket clients with shared handlers."""

    def __init__(
        self,
        settings: Settings,
        hub: WsMarketHub,
        recon: ReconciliationService | None = None,
    ) -> None:
        self._settings = settings
        self._hub = hub
        self._recon = recon

        def _on_market(msg: dict) -> None:
            self._hub.apply_raw(msg)

        def _on_user(msg: dict) -> None:
            t = str(msg.get("type", "")).upper()
            if t == "TRADE" and self._recon:
                self._recon.record_ws_trade(msg)
            elif str(msg.get("event_type", "")).lower() == "order" and self._recon:
                self._recon.record_ws_order_event(msg)

        self._mkt = PolymarketWsMarket(settings, on_event=_on_market)
        self._usr = PolymarketWsUser(settings, on_event=_on_user)

    def start_market(self, asset_ids: list[str]) -> None:
        if not self._settings.enable_ws:
            log.info("ws_disabled")
            return
        self._mkt.start_background(asset_ids)

    def start_user(self, condition_ids: list[str]) -> None:
        if not self._settings.enable_ws:
            return
        self._usr.start_background(condition_ids)

    def stop(self) -> None:
        self._mkt.stop()
        self._usr.stop()

    @property
    def market_latency_ms(self) -> float | None:
        return self._mkt.latency_ms
