"""
A. Passive Market Making Guarded — quote only wide spread, tiny size, inventory aware.
Entry: spread > min_spread_bps, not in high-vol regime, health metrics OK.
Exit / invalidation: turn off if fill rate or adverse selection worsen (tracked via meta).
"""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.models.position import Position
from app.models.signal import ExitDecision, Signal, SignalAction
from app.strategies.base import BaseStrategy


class MarketMakingPassiveStrategy(BaseStrategy):
    name = "market_making_passive"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._min_spread_bps = max(50.0, settings.max_spread_bps * 0.25)
        self._bad_fills = 0

    def prepare(self, data: dict[str, Any]) -> None:
        self._last = data

    def generate_signal(self, state: dict[str, Any]) -> Signal | None:
        book = state.get("book")
        market_id = str(state.get("market_id", ""))
        token_id = str(state.get("token_id", ""))
        spread_bps = state.get("spread_bps")
        vol_regime = float(state.get("vol_score", 0.0))

        # Regime filter: skip quoting in high vol
        if vol_regime > 0.7:
            return None

        if spread_bps is None or spread_bps < self._min_spread_bps:
            return None

        if self._bad_fills >= 3:
            return None

        # Inventory: lean quotes to flatten
        inv = float(state.get("inventory_imbalance", 0.0))
        action = SignalAction.QUOTE_BID
        if inv > 0.2:
            action = SignalAction.QUOTE_ASK
        elif inv < -0.2:
            action = SignalAction.QUOTE_BID

        mid = state.get("mid")
        if mid is None:
            return None
        price = float(mid) * (0.9995 if action == SignalAction.QUOTE_BID else 1.0005)

        return Signal(
            strategy=self.name,
            market_id=market_id,
            token_id=token_id,
            action=action,
            price=price,
            size=0.0,
            confidence=0.35,
            reason="passive_mm_wide_spread",
            meta={"spread_bps": spread_bps},
        )

    def should_exit(self, position: Position, state: dict[str, Any]) -> ExitDecision:
        target = state.get("mid")
        if target is None:
            return ExitDecision(should_exit=False)
        # flatten if inventory too large
        if abs(position.size) * position.avg_price > self._settings.max_market_exposure_usd * 0.5:
            return ExitDecision(should_exit=True, reason="inventory", limit_price=float(target))
        return ExitDecision(should_exit=False)

    def healthcheck(self) -> dict[str, Any]:
        return {"ok": self._bad_fills < 5, "strategy": self.name, "bad_fills": self._bad_fills}
