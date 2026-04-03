"""Analysis package — fair value, live/historical features, scoring.

Heavy submodules are loaded lazily so `import app.analysis` stays lightweight and tests
avoid pulling the full tree until a symbol is accessed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "FairValueEngine",
    "HistoricalAnalyzer",
    "LiveMarketAnalyzer",
    "MarketScorer",
]

if TYPE_CHECKING:
    from app.analysis.fair_value_engine import FairValueEngine
    from app.analysis.historical_analyzer import HistoricalAnalyzer
    from app.analysis.live_market_analyzer import LiveMarketAnalyzer
    from app.analysis.market_scorer import MarketScorer


def __getattr__(name: str) -> Any:
    if name == "FairValueEngine":
        from app.analysis.fair_value_engine import FairValueEngine

        return FairValueEngine
    if name == "HistoricalAnalyzer":
        from app.analysis.historical_analyzer import HistoricalAnalyzer

        return HistoricalAnalyzer
    if name == "LiveMarketAnalyzer":
        from app.analysis.live_market_analyzer import LiveMarketAnalyzer

        return LiveMarketAnalyzer
    if name == "MarketScorer":
        from app.analysis.market_scorer import MarketScorer

        return MarketScorer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
