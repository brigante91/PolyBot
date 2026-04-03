"""PnL tracking for risk engine."""

from __future__ import annotations

from app.risk.risk_engine import RiskEngine


class PnLService:
    def __init__(self, risk: RiskEngine) -> None:
        self._risk = risk

    def record_realized(self, delta: float) -> None:
        self._risk.state.realized_today += delta
        if delta < 0:
            self._risk.state.consecutive_losses += 1
        elif delta > 0:
            self._risk.state.consecutive_losses = 0

    def mark_adverse_fill(self) -> None:
        from app.utils.time import utc_now

        self._risk.state.last_adverse_fill_at = utc_now()
