from __future__ import annotations

from app.config import Settings
from app.models.context import MarketContext
from app.models.order import OrderIntent, OrderSide, TimeInForce
from app.strategy.base_strategy import StrategyBase


class MomentumMicroStrategy(StrategyBase):
    name = "momentum_micro"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def can_trade(self, ctx: MarketContext) -> bool:
        if abs(ctx.live.mid_change_1m_bps) < 15.0:
            return False
        fv = ctx.fair_value
        if fv is not None and fv.confidence < 0.35:
            return False
        return ctx.live.response_score >= 0.4 and float(ctx.score_total) >= self._settings.score_min_tradable

    def score(self, ctx: MarketContext) -> float:
        mom = min(1.0, abs(ctx.live.mid_change_1m_bps) / 200.0)
        base = mom * 0.65 + ctx.live.response_score * 0.35
        if ctx.fair_value is not None:
            base *= 0.6 + 0.4 * float(ctx.fair_value.confidence)
        return base

    def build_order_intent(self, ctx: MarketContext) -> OrderIntent | None:
        tid = ctx.candidate.primary_token_id()
        mid = ctx.live.book.mid() if ctx.live.book else None
        if not tid or mid is None:
            return None
        side = OrderSide.BUY if ctx.live.mid_change_1m_bps > 0 else OrderSide.SELL
        px = float(mid)
        notional = self._settings.max_order_size_usd * 0.4
        size = notional / max(px, 1e-6)
        return OrderIntent(
            market_id=ctx.candidate.market_id,
            token_id=tid,
            side=side,
            price=px,
            size=size,
            tif=TimeInForce.GTC,
        )
