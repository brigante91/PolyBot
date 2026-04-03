"""Simple correlation / exposure grouping (e.g. crypto majors) for portfolio caps."""

from __future__ import annotations

from app.config import Settings


class CorrelationManager:
    """
    Groups markets by keyword in category or slug (BTC, ETH, SOL).
    Enforces max_exposure_group_usd per group in addition to per-market limits.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._group_exposure: dict[str, float] = {}

    def group_key(self, category: str | None, slug: str | None, question: str) -> str:
        blob = f"{category or ''} {slug or ''} {question}".upper()
        for tag in ("BTC", "BITCOIN", "ETH", "ETHEREUM", "SOL", "SOLANA"):
            if tag in blob:
                return tag.split()[0][:3]
        return "OTHER"

    def current_group_exposure(self, group: str) -> float:
        return self._group_exposure.get(group, 0.0)

    def add_exposure(self, group: str, usd: float) -> None:
        self._group_exposure[group] = self._group_exposure.get(group, 0.0) + usd

    def would_exceed(self, group: str, add_usd: float) -> bool:
        return self.current_group_exposure(group) + add_usd > self._settings.max_exposure_group_usd
