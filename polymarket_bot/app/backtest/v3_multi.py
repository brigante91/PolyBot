"""
Multi-market backtest entrypoints — prefer `MultiMarketBacktest` in `v4_multi_engine`.
"""

from __future__ import annotations

from app.backtest.v4_multi_engine import MultiMarketBacktest, MultiMarketResult

__all__ = ["MultiMarketBacktest", "MultiMarketResult"]
