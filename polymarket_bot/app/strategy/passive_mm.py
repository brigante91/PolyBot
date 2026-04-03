"""Passive market making — small size, wide spread only."""

from __future__ import annotations

from app.config import Settings
from app.models.context import MarketContext
from app.models.order import OrderIntent, OrderSide, TimeInForce
from app.strategy.base_strategy import StrategyBase


class PassiveMarketMakingStrategy(StrategyBase):
    name = "passive_market_making"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def can_trade(self, ctx: MarketContext) -> bool:
        sp = ctx.live.spread_bps
        if sp is None:
            return False
        fv = ctx.fair_value
        if fv is not None and fv.confidence < 0.28:
            return False
        return sp >= max(40.0, self._settings.max_spread_bps * 0.2) and float(ctx.score_total) >= self._settings.score_min_tradable

    def score(self, ctx: MarketContext) -> float:
        sp = ctx.live.spread_bps or 9999.0
        base = min(1.0, max(0.0, 1.0 - sp / max(self._settings.max_spread_bps, 1.0))) * 0.6 + float(ctx.score_total) * 0.4
        if ctx.fair_value is not None:
            base *= 0.55 + 0.45 * float(ctx.fair_value.confidence)
        return base

    def build_order_intent(self, ctx: MarketContext) -> OrderIntent | None:
        tid = ctx.candidate.primary_token_id()
        mid = ctx.live.book.mid() if ctx.live.book else None
        if not tid or mid is None:
            return None
        px = float(mid) * 0.999
        notional = self._settings.max_order_size_usd * 0.25
        size = notional / max(px, 1e-6)
        return OrderIntent(
            market_id=ctx.candidate.market_id,
            token_id=tid,
            side=OrderSide.BUY,
            price=px,
            size=size,
            tif=TimeInForce.GTC,
        )
