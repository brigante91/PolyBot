"""Filter Gamma markets by liquidity, volume, time to expiry, spread."""

from __future__ import annotations

from datetime import datetime, timezone

from app.clients.gamma_client import GammaClient
from app.config import Settings
from app.models.market import GammaMarket


class MarketDiscoveryService:
    def __init__(self, settings: Settings, gamma: GammaClient) -> None:
        self._settings = settings
        self._gamma = gamma

    def discover(self, *, max_pages: int = 20) -> list[GammaMarket]:
        markets = self._gamma.fetch_all_active_markets(max_pages=max_pages)
        return [m for m in markets if self._passes_filters(m)]

    def _passes_filters(self, m: GammaMarket) -> bool:
        if m.closed or not m.active:
            return False
        if self._settings.min_liquidity > 0:
            if m.liquidity_num is None or m.liquidity_num < self._settings.min_liquidity:
                return False
        if m.end_date:
            if m.end_date.tzinfo is None:
                end = m.end_date.replace(tzinfo=timezone.utc)
            else:
                end = m.end_date
            if end < datetime.now(timezone.utc):
                return False
        # Spread from Gamma raw if present (optional filter)
        spr = m.raw.get("spread")
        if spr is not None:
            try:
                # Gamma may expose spread as decimal or bps — interpret as decimal of price width
                s = float(spr)
                mid = m.raw.get("lastTradePrice")
                if mid:
                    bps = s / float(mid) * 10000.0
                    if bps > self._settings.max_spread_bps:
                        return False
            except (TypeError, ValueError, ZeroDivisionError):
                pass
        return True
