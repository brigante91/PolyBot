"""PnL by market and strategy."""

from __future__ import annotations

from collections import defaultdict


class PnLTracker:
    def __init__(self) -> None:
        self._mkt: dict[str, float] = defaultdict(float)
        self._strat: dict[str, float] = defaultdict(float)

    def add(self, *, market_id: str, strategy_id: str, pnl_usd: float) -> None:
        self._mkt[market_id] += pnl_usd
        self._strat[strategy_id] += pnl_usd

    def by_market(self) -> dict[str, float]:
        return dict(self._mkt)

    def by_strategy(self) -> dict[str, float]:
        return dict(self._strat)
