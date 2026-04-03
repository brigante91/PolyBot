"""
C. Fair Value Gap / Cross-Market — proxy via implied prob vs mid of related token (user supplies correlation in state).
No risk-free arb claim; only trade if edge > fee + spread + slippage buffer.
"""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.models.position import Position
from app.models.signal import ExitDecision, Signal, SignalAction
from app.strategies.base import BaseStrategy
from app.utils.math_utils import bps_to_fraction


class FairValueGapStrategy(BaseStrategy):
    name = "fair_value_gap"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def prepare(self, data: dict[str, Any]) -> None:
        self._ref = data.get("reference_prob")

    def generate_signal(self, state: dict[str, Any]) -> Signal | None:
        p_impl = state.get("implied_prob")
        p_ref = state.get("reference_prob", self._ref)
        if p_impl is None or p_ref is None:
            return None
        edge = abs(float(p_impl) - float(p_ref))
        costs = (
            bps_to_fraction(self._settings.max_spread_bps)
            + bps_to_fraction(self._settings.paper_fee_bps)
            + bps_to_fraction(self._settings.paper_slippage_bps)
        )
        if edge < costs * 1.5:
            return None
        side = SignalAction.BUY if float(p_ref) > float(p_impl) else SignalAction.SELL
        return Signal(
            strategy=self.name,
            market_id=str(state.get("market_id", "")),
            token_id=str(state.get("token_id", "")),
            action=side,
            price=float(p_impl),
            size=0.0,
            confidence=0.45,
            reason="fvg_edge",
            meta={"edge": edge},
        )

    def should_exit(self, position: Position, state: dict[str, Any]) -> ExitDecision:
        if state.get("edge_gone"):
            return ExitDecision(should_exit=True, reason="invalidation")
        return ExitDecision(should_exit=False)

    def healthcheck(self) -> dict[str, Any]:
        return {"ok": True, "strategy": self.name}
