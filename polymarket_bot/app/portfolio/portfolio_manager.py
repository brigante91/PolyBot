"""Global multi-market portfolio view and aggregate gates."""

from __future__ import annotations

from app.config import Settings
from app.portfolio.position_registry import PositionRegistry
from app.portfolio.pnl_tracker import PnLTracker
from app.risk.risk_engine import RiskEngine


class PortfolioManager:
    def __init__(
        self,
        settings: Settings,
        risk: RiskEngine,
        registry: PositionRegistry,
        pnl: PnLTracker,
    ) -> None:
        self._settings = settings
        self._risk = risk
        self._registry = registry
        self._pnl = pnl

    @property
    def available_bankroll_usd(self) -> float:
        used = self._risk.state.exposure.total
        return max(0.0, self._settings.max_total_exposure_usd - used)

    def open_positions_count(self) -> int:
        return self._risk.state.open_position_count

    def can_open_more(self) -> bool:
        return self._risk.state.open_position_count < self._settings.max_concurrent_positions
