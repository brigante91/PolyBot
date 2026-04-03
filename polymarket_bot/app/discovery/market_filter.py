"""Fast exclusion of non-tradable or unfavorable markets."""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import Settings
from app.models.candidate import CandidateMarket


class MarketFilter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def filter(self, markets: list[CandidateMarket]) -> tuple[list[CandidateMarket], list[tuple[str, str]]]:
        kept: list[CandidateMarket] = []
        rejected: list[tuple[str, str]] = []
        now = datetime.now(timezone.utc)
        for m in markets:
            reason = self._reject_reason(m, now)
            if reason:
                rejected.append((m.market_id, reason))
                continue
            kept.append(m)
        return kept, rejected

    def _reject_reason(self, m: CandidateMarket, now: datetime) -> str | None:
        if not m.active:
            return "inactive"

        if m.liquidity is not None and m.liquidity < self._settings.min_liquidity:
            return "low_liquidity"

        if m.volume is not None and m.volume < self._settings.min_volume_24h:
            return "low_volume"

        if m.spread_estimate_bps is not None and m.spread_estimate_bps > self._settings.max_spread_bps:
            return "wide_spread_gamma"

        if m.end_date:
            end = m.end_date if m.end_date.tzinfo else m.end_date.replace(tzinfo=timezone.utc)
            ttr = (end - now).total_seconds() / 60.0
            if ttr < self._settings.min_time_to_resolution_minutes:
                return "too_close_to_resolution"
            max_m = self._settings.fast_resolution_max_minutes
            if max_m is not None and ttr > max_m:
                return "not_fast_window"

        if not m.tokens:
            return "no_tokens"

        return None