"""Combine liquidity, execution quality, history, risk penalty into a single score."""

from __future__ import annotations

from app.config import Settings
from app.models.candidate import CandidateMarket
from app.models.context import HistoricalProfile, LiveFeatures


class MarketScorer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def score(
        self,
        candidate: CandidateMarket,
        live: LiveFeatures,
        hist: HistoricalProfile,
    ) -> dict[str, float | bool]:
        liq = candidate.liquidity or 0.0
        liquidity_score = min(1.0, liq / max(self._settings.min_liquidity * 3, 1.0))

        sp = live.spread_bps
        if sp is None:
            sp = candidate.spread_estimate_bps or self._settings.max_spread_bps
        spread_score = max(0.0, 1.0 - sp / max(self._settings.max_spread_bps, 1.0))

        depth_score = min(1.0, live.depth_top_usd / max(self._settings.min_orderbook_depth_usd * 4, 1.0))
        exec_score = 0.45 * spread_score + 0.35 * depth_score + 0.20 * live.response_score

        hist_score = 0.4 * hist.edge_stability + 0.3 * hist.fill_quality_avg + 0.3 * min(1.0, hist.sample_size / 100.0)

        risk_penalty = 0.0
        if liq < self._settings.min_liquidity:
            risk_penalty += 0.15
        if sp > self._settings.max_spread_bps * 0.8:
            risk_penalty += 0.1

        total = (
            0.30 * liquidity_score
            + 0.35 * exec_score
            + 0.25 * hist_score
            + 0.10 * (1.0 - min(0.9, risk_penalty))
        )
        recommended = total >= self._settings.score_min_tradable and risk_penalty < 0.4

        return {
            "score_total": round(total, 4),
            "liquidity_score": round(liquidity_score, 4),
            "execution_score": round(exec_score, 4),
            "historical_score": round(hist_score, 4),
            "risk_penalty": round(risk_penalty, 4),
            "recommended": recommended,
        }
