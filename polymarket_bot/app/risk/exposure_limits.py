"""Exposure tracking against configured USD caps."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import Settings


@dataclass
class ExposureState:
    per_market: dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    open_order_count: int = 0


class ExposureLimits:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def market_exposure(self, state: ExposureState, market_id: str) -> float:
        return state.per_market.get(market_id, 0.0)

    def would_exceed_market(self, state: ExposureState, market_id: str, add_usd: float) -> bool:
        return self.market_exposure(state, market_id) + add_usd > self._settings.max_market_exposure_usd

    def would_exceed_total(self, state: ExposureState, add_usd: float) -> bool:
        return state.total + add_usd > self._settings.max_total_exposure_usd

    def max_open_orders_exceeded(self, state: ExposureState) -> bool:
        return state.open_order_count >= self._settings.max_open_orders
