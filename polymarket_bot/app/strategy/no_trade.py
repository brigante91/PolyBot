from __future__ import annotations

from app.models.context import MarketContext
from app.models.order import OrderIntent
from app.strategy.base_strategy import StrategyBase


class NoTradeStrategy(StrategyBase):
    name = "no_trade"

    def can_trade(self, ctx: MarketContext) -> bool:
        return False

    def score(self, ctx: MarketContext) -> float:
        return 0.0

    def build_order_intent(self, ctx: MarketContext) -> OrderIntent | None:
        return None

    def explain(self, ctx: MarketContext) -> str:
        return "no_trade: explicit sentinel strategy"
