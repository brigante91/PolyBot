"""
Legacy strategy plug-ins (signal-style API for backtests).

V3 canonical implementations live in `app.strategy` (intent-based). New code should
import from `app.strategy`; this package remains for backward compatibility.
"""

from app.config import Settings
from app.strategies.base import BaseStrategy
from app.strategies.event_momentum_guarded import EventMomentumGuardedStrategy
from app.strategies.fair_value_gap import FairValueGapStrategy
from app.strategies.market_making_passive import MarketMakingPassiveStrategy
from app.strategies.mean_reversion_micro import MeanReversionMicroStrategy

REGISTRY: dict[str, type[BaseStrategy]] = {
    "market_making_passive": MarketMakingPassiveStrategy,
    # Alias aligned with `app.strategy` naming (V4)
    "passive_market_making": MarketMakingPassiveStrategy,
    "mean_reversion_micro": MeanReversionMicroStrategy,
    "fair_value_gap": FairValueGapStrategy,
    "event_momentum_guarded": EventMomentumGuardedStrategy,
}


def get_strategy(name: str, *, settings: Settings) -> BaseStrategy:
    cls = REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"Unknown strategy: {name}")
    return cls(settings=settings)  # type: ignore[misc]
