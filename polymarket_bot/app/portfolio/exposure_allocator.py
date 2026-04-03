"""Dynamic size from score, confidence, residual risk, liquidity."""

from __future__ import annotations

from app.config import Settings
from app.models.context import MarketContext
from app.risk.risk_engine import RiskEngine


class ExposureAllocator:
    def __init__(self, settings: Settings, risk: RiskEngine) -> None:
        self._settings = settings
        self._risk = risk

    def recommend_usd(self, ctx: MarketContext, confidence: float) -> float:
        bankroll = max(self._settings.max_total_exposure_usd, 1000.0)
        sp = ctx.live.spread_bps
        base = self._risk.suggest_size(
            bankroll_usd=bankroll,
            confidence=confidence,
            spread_bps=sp,
            mid_price=ctx.live.book.mid() if ctx.live.book else None,
        )
        scale = 0.5 + 0.5 * float(ctx.score_total)
        out = base * scale
        return min(out, self._settings.max_order_size_usd, self._settings.max_market_exposure_usd * 0.5)
