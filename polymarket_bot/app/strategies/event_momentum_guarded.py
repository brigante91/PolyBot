"""
D. Event Momentum Guarded — breakout after volume confirmation; cooldown after losses.
Avoid late chasing; no trade if momentum score weak.
"""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.models.position import Position
from app.models.signal import ExitDecision, Signal, SignalAction
from app.strategies.base import BaseStrategy


class EventMomentumGuardedStrategy(BaseStrategy):
    name = "event_momentum_guarded"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cooldown = 0
        self._last_mid: float | None = None

    def prepare(self, data: dict[str, Any]) -> None:
        mid = data.get("mid")
        if isinstance(mid, (int, float)):
            self._last_mid = float(mid)

    def generate_signal(self, state: dict[str, Any]) -> Signal | None:
        if self._cooldown > 0:
            self._cooldown -= 1
            return None
        mom = float(state.get("momentum_score", 0.0))
        vol_conf = float(state.get("volume_confirm", 0.0))
        late = bool(state.get("late_chase", False))
        if late or vol_conf < 0.5 or mom < 0.6:
            return None
        mid = state.get("mid")
        if mid is None:
            return None
        return Signal(
            strategy=self.name,
            market_id=str(state.get("market_id", "")),
            token_id=str(state.get("token_id", "")),
            action=SignalAction.BUY,
            price=float(mid),
            size=0.0,
            confidence=min(mom, 0.85),
            reason="guarded_momentum",
            meta={},
        )

    def should_exit(self, position: Position, state: dict[str, Any]) -> ExitDecision:
        if state.get("stop_hit"):
            self._cooldown = 5
            return ExitDecision(should_exit=True, reason="stop")
        return ExitDecision(should_exit=False)

    def healthcheck(self) -> dict[str, Any]:
        return {"ok": True, "strategy": self.name, "cooldown": self._cooldown}
