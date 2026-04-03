"""Pick best strategy per market or NO_TRADE."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.models.context import MarketContext
from app.models.decision import OperationalAction
from app.strategy.base_strategy import StrategyBase
from app.strategy.fair_value_gap import FairValueGapStrategy
from app.strategy.mean_reversion import MeanReversionMicroStrategy
from app.strategy.momentum import MomentumMicroStrategy
from app.strategy.no_trade import NoTradeStrategy
from app.strategy.passive_mm import PassiveMarketMakingStrategy


@dataclass
class SelectionResult:
    strategy_id: str
    confidence: float
    action: OperationalAction
    rationale: str


class StrategySelector:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._strategies: list[StrategyBase] = [
            PassiveMarketMakingStrategy(settings),
            MeanReversionMicroStrategy(settings),
            MomentumMicroStrategy(settings),
            FairValueGapStrategy(settings),
            NoTradeStrategy(),
        ]
        self._by_name = {s.name: s for s in self._strategies}

    def select(self, ctx: MarketContext) -> SelectionResult:
        best: StrategyBase | None = None
        best_score = -1.0
        for s in self._strategies:
            if s.name == "no_trade":
                continue
            if not s.can_trade(ctx):
                continue
            sc = s.score(ctx)
            if sc > best_score:
                best_score = sc
                best = s
        if best is None or best_score < 0.15:
            return SelectionResult(
                strategy_id="no_trade",
                confidence=0.0,
                action=OperationalAction.NO_TRADE,
                rationale="no_strategy_passed_threshold",
            )
        action = OperationalAction.ENTER_LIMIT_BUY
        if best.name == "passive_market_making":
            action = OperationalAction.PASSIVE_QUOTE
        return SelectionResult(
            strategy_id=best.name,
            confidence=min(1.0, best_score),
            action=action,
            rationale=f"selected_{best.name}",
        )

    def build_intent(self, ctx: MarketContext, strategy_id: str):
        s = self._by_name.get(strategy_id)
        if s is None or strategy_id == "no_trade":
            return None
        return s.build_order_intent(ctx)
