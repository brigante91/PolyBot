"""Multi-market replay driver — feeds orchestrator with recorded snapshots (stub hooks)."""

from __future__ import annotations

from typing import Any


class ReplayFeed:
    """TODO: load CSV/JSONL of book snapshots per market for offline replay."""

    def __init__(self, path: str | None = None) -> None:
        self._path = path

    def iter_ticks(self) -> Any:
        if not self._path:
            return iter(())
        # Placeholder for future implementation
        return iter(())
