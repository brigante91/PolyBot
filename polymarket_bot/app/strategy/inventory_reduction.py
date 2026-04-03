"""Reduce existing inventory — requires position context (extended in future)."""

from __future__ import annotations

from app.config import Settings
from app.models.context import MarketContext
from app.models.order import OrderIntent, OrderSide, TimeInForce
from app.strategy.base_strategy import StrategyBase


class InventoryReductionStrategy(StrategyBase):
    name = "inventory_reduction"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def can_trade(self, ctx: MarketContext) -> bool:
        # Until position is wired on MarketContext, stay inactive.
        _ = ctx
        return False

    def score(self, ctx: MarketContext) -> float:
        return 0.0

    def build_order_intent(self, ctx: MarketContext) -> OrderIntent | None:
        return None

    def explain(self, ctx: MarketContext) -> str:
        return f"{self.name}: disabled until position_registry is attached to context"
