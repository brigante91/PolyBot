from __future__ import annotations

from app.config import Settings
from app.models.context import MarketContext
from app.models.order import OrderIntent, OrderSide, TimeInForce
from app.strategy.base_strategy import StrategyBase


class MeanReversionMicroStrategy(StrategyBase):
    name = "mean_reversion_micro"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def can_trade(self, ctx: MarketContext) -> bool:
        sp = ctx.live.spread_bps
        if sp is None or sp > self._settings.max_spread_bps * 0.85:
            return False
        fv = ctx.fair_value
        if fv is not None and fv.confidence < 0.25:
            return False
        return ctx.live.depth_top_usd >= self._settings.min_orderbook_depth_usd

    def score(self, ctx: MarketContext) -> float:
        z = abs(ctx.live.mid_change_1m_bps) / 100.0
        base = min(1.0, z) * 0.7 + float(ctx.score_total) * 0.3
        if ctx.fair_value is not None:
            base *= 0.5 + 0.5 * abs(ctx.fair_value.fair_prob - ctx.fair_value.market_prob)
        return base

    def build_order_intent(self, ctx: MarketContext) -> OrderIntent | None:
        tid = ctx.candidate.primary_token_id()
        mid = ctx.live.book.mid() if ctx.live.book else None
        if not tid or mid is None:
            return None
        side = OrderSide.SELL if ctx.live.mid_change_1m_bps > 0 else OrderSide.BUY
        px = float(mid)
        notional = self._settings.max_order_size_usd * 0.35
        size = notional / max(px, 1e-6)
        return OrderIntent(
            market_id=ctx.candidate.market_id,
            token_id=tid,
            side=side,
            price=px,
            size=size,
            tif=TimeInForce.GTC,
        )
