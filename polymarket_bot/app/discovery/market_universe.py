"""Scan active Polymarket markets and build a uniform candidate universe."""

from __future__ import annotations

from datetime import datetime, timezone

from app.clients.gamma_client import GammaClient
from app.config import Settings
from app.discovery.market_metadata import infer_category
from app.models.candidate import CandidateMarket
from app.models.market import GammaMarket, OutcomeToken, TokenSide


class MarketUniverseScanner:
    """Discover all active candidate markets — not a single fixed market."""

    def __init__(self, settings: Settings, gamma: GammaClient) -> None:
        self._settings = settings
        self._gamma = gamma

    def scan(self) -> list[CandidateMarket]:
        raw_markets = self._gamma.fetch_all_active_markets(max_pages=self._settings.universe_scan_pages)
        out: list[CandidateMarket] = []
        for m in raw_markets[: self._settings.universe_max_markets]:
            out.append(self._to_candidate(m))
        return out

    def _to_candidate(self, m: GammaMarket) -> CandidateMarket:
        spread_bps: float | None = None
        mid = m.raw.get("lastTradePrice")
        spr = m.raw.get("spread")
        if mid and spr is not None:
            try:
                mf, sf = float(mid), float(spr)
                if mf > 0:
                    spread_bps = sf / mf * 10000.0
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        tokens: list[OutcomeToken] = []
        for ot in m.map_tokens_yes_no():
            tokens.append(ot)
        if not tokens and m.clob_token_ids:
            for tid in m.clob_token_ids:
                tokens.append(OutcomeToken(token_id=tid, side=TokenSide.UNKNOWN))

        end = m.end_date
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        return CandidateMarket(
            market_id=m.id,
            question=m.question or "",
            slug=m.slug,
            tokens=tokens,
            active=m.active and not m.closed,
            end_date=end,
            category=infer_category(m.raw),
            liquidity=m.liquidity_num,
            volume=m.volume_24hr or float(m.raw.get("volumeNum") or 0) or None,
            spread_estimate_bps=spread_bps,
            tradable=True,
            raw=m.raw,
        )
