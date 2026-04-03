"""Registry of open exposures per market / token."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PositionRecord:
    market_id: str
    token_id: str
    size: float = 0.0
    avg_price: float = 0.0
    strategy_id: str = "no_trade"


class PositionRegistry:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], PositionRecord] = {}

    def count_open_markets(self) -> int:
        return sum(1 for p in self._by_key.values() if abs(p.size) > 1e-9)

    def get(self, market_id: str, token_id: str) -> PositionRecord | None:
        return self._by_key.get((market_id, token_id))

    def upsert(self, rec: PositionRecord) -> None:
        self._by_key[(rec.market_id, rec.token_id)] = rec
