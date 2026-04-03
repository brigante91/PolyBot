"""
B. Mean Reversion Microstructure — short deviation from local mid/VWAP proxy.
Entry: z-score of price vs mid small, spread and depth OK.
Exit: target hit or timeout bars.
"""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.models.position import Position
from app.models.signal import ExitDecision, Signal, SignalAction
from app.strategies.base import BaseStrategy


class MeanReversionMicroStrategy(BaseStrategy):
    name = "mean_reversion_micro"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._history: list[float] = []

    def prepare(self, data: dict[str, Any]) -> None:
        mid = data.get("mid")
        if isinstance(mid, (int, float)):
            self._history.append(float(mid))
            self._history = self._history[-64:]

    def generate_signal(self, state: dict[str, Any]) -> Signal | None:
        spread_bps = state.get("spread_bps")
        if spread_bps is None or spread_bps > self._settings.max_spread_bps * 0.8:
            return None
        depth_ok = float(state.get("depth_usd", 0.0)) >= self._settings.min_orderbook_depth_usd
        if not depth_ok:
            return None
        if len(self._history) < 8:
            return None
        last = self._history[-1]
        mu = sum(self._history) / len(self._history)
        var = sum((x - mu) ** 2 for x in self._history) / max(len(self._history) - 1, 1)
        sigma = var**0.5 or 1e-9
        z = (last - mu) / sigma
        if abs(z) < 0.75:
            return None
        side = SignalAction.SELL if z > 0 else SignalAction.BUY
        return Signal(
            strategy=self.name,
            market_id=str(state.get("market_id", "")),
            token_id=str(state.get("token_id", "")),
            action=side,
            price=last,
            size=0.0,
            confidence=min(abs(z) / 3.0, 1.0),
            reason="mean_reversion_z",
            meta={"z": z},
        )

    def should_exit(self, position: Position, state: dict[str, Any]) -> ExitDecision:
        bars = int(state.get("bars_held", 0))
        if bars > 20:
            return ExitDecision(should_exit=True, reason="timeout")
        return ExitDecision(should_exit=False)

    def healthcheck(self) -> dict[str, Any]:
        return {"ok": True, "strategy": self.name, "hist": len(self._history)}
