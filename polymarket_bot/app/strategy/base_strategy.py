"""Strategy plug-in interface — produces intents only; never sends orders."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.context import MarketContext
from app.models.order import OrderIntent


class StrategyBase(ABC):
    name: str = "base"

    @abstractmethod
    def can_trade(self, ctx: MarketContext) -> bool:
        """Whether this strategy applies to current market conditions."""

    @abstractmethod
    def score(self, ctx: MarketContext) -> float:
        """Relative strength in [0,1] for selector ranking."""

    @abstractmethod
    def build_order_intent(self, ctx: MarketContext) -> OrderIntent | None:
        """Return limit intent or None (e.g. quote-only handled upstream)."""
