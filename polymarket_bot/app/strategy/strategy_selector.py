"""Pick best strategy per market or NO_TRADE — with runner-up and explainability."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import Settings
from app.models.context import MarketContext
from app.models.decision import OperationalAction
from app.strategy.base_strategy import StrategyBase
from app.strategy.fair_value_gap import FairValueGapStrategy
from app.strategy.inventory_reduction import InventoryReductionStrategy
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
    second_best_id: str | None = None
    second_best_score: float | None = None
    explain_selected: str = ""
    explain_rejected: list[str] = field(default_factory=list)


class StrategySelector:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._strategies: list[StrategyBase] = [
            PassiveMarketMakingStrategy(settings),
            MeanReversionMicroStrategy(settings),
            MomentumMicroStrategy(settings),
            FairValueGapStrategy(settings),
            InventoryReductionStrategy(settings),
            NoTradeStrategy(),
        ]
        self._by_name = {s.name: s for s in self._strategies}

    def select(self, ctx: MarketContext) -> SelectionResult:
        scored: list[tuple[StrategyBase, float]] = []
        rejected: list[str] = []
        for s in self._strategies:
            if s.name == "no_trade":
                continue
            if not s.can_trade(ctx):
                rejected.append(f"{s.name}: {s.explain(ctx)[:80]}")
                continue
            sc = s.score(ctx)
            scored.append((s, sc))
        scored.sort(key=lambda x: -x[1])

        if not scored or scored[0][1] < 0.15:
            return SelectionResult(
                strategy_id="no_trade",
                confidence=0.0,
                action=OperationalAction.NO_TRADE,
                rationale="no_strategy_passed_threshold",
                explain_rejected=rejected[:12],
                explain_selected="no_trade: below threshold or no candidate",
            )

        best, best_score = scored[0]
        second_id = None
        second_sc = None
        if len(scored) > 1:
            second_id = scored[1][0].name
            second_sc = scored[1][1]

        action = OperationalAction.ENTER_LIMIT_BUY
        if best.name == "passive_market_making":
            action = OperationalAction.PASSIVE_QUOTE

        return SelectionResult(
            strategy_id=best.name,
            confidence=min(1.0, best_score),
            action=action,
            rationale=f"selected_{best.name}",
            second_best_id=second_id,
            second_best_score=second_sc,
            explain_selected=best.explain(ctx),
            explain_rejected=rejected[:12],
        )

    def build_intent(self, ctx: MarketContext, strategy_id: str):
        s = self._by_name.get(strategy_id)
        if s is None or strategy_id == "no_trade":
            return None
        return s.build_order_intent(ctx)
