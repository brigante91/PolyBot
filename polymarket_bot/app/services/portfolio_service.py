"""In-memory portfolio (paper/live); sync from Data API optional."""

from __future__ import annotations

from app.models.position import Position


class PortfolioService:
    def __init__(self) -> None:
        self._positions: dict[tuple[str, str], Position] = {}

    def get(self, market_id: str, token_id: str) -> Position | None:
        return self._positions.get((market_id, token_id))

    def upsert(self, pos: Position) -> None:
        self._positions[(pos.market_id, pos.token_id)] = pos

    def all_positions(self) -> list[Position]:
        return list(self._positions.values())

    def gross_exposure_usd(self) -> float:
        total = 0.0
        for p in self._positions.values():
            total += abs(p.size * p.avg_price)
        return total
