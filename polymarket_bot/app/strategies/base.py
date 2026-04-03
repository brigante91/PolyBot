"""Strategy interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.position import Position
from app.models.signal import ExitDecision, Signal


class BaseStrategy(ABC):
    """Common interface; implementations must fail closed to no-trade when weak."""

    name: str = "base"

    @abstractmethod
    def prepare(self, data: dict[str, Any]) -> None:
        """Ingest normalized market state (book, mid, metadata)."""

    @abstractmethod
    def generate_signal(self, state: dict[str, Any]) -> Signal | None:
        """Return a signal or None if no trade."""

    @abstractmethod
    def should_exit(self, position: Position, state: dict[str, Any]) -> ExitDecision:
        """Exit logic for open positions."""

    def healthcheck(self) -> dict[str, Any]:
        return {"ok": True, "strategy": self.name}
