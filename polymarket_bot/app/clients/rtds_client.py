"""
Polymarket RTDS (real-time data stream) — optional WebSocket for underlying/index prices.

Wire `ENABLE_RTDS=true` and `RTDS_WS_URL` when your deployment has a documented feed.
Implementation is intentionally minimal; use `SpotPriceClient` for REST fallback today.
"""

from __future__ import annotations

from app.config import Settings
from app.logger import get_logger

log = get_logger("rtds")


class RtdsClient:
    """Placeholder: subscribe to RTDS and push prices into a callback or shared cache."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def start_if_enabled(self) -> None:
        if not self._settings.enable_rtds or not (self._settings.rtds_ws_url or "").strip():
            return
        log.info("rtds_stub", hint="enable SpotPriceClient REST or implement RTDS subscribe")
