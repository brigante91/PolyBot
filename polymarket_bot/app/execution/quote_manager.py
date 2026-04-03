"""Maker-first quote lifecycle: cancel/replace hooks (REST v1 — extend with WS)."""

from __future__ import annotations

from app.config import Settings
from app.logger import get_logger

log = get_logger("quote_manager")


class QuoteManager:
    """Tracks logical quotes per market; integrates with order router in future."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def should_refresh(self, market_id: str, mid_move_bps: float) -> bool:
        return abs(mid_move_bps) > 5.0
