from __future__ import annotations

from app.config import Settings
from app.models.context import MarketContext
from app.models.order import OrderIntent, OrderSide, TimeInForce
from app.strategy.base_strategy import StrategyBase
from app.utils.math_utils import bps_to_fraction


class FairValueGapStrategy(StrategyBase):
    name = "fair_value_gap"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def can_trade(self, ctx: MarketContext) -> bool:
        p = ctx.live.book.mid() if ctx.live.book else None
        if p is None:
            return False
        ref = float(ctx.historical.expectancy) + 0.5
        edge = abs(float(p) - ref)
        costs = bps_to_fraction(self._settings.max_spread_bps) + bps_to_fraction(self._settings.paper_fee_bps)
        return edge > costs * 1.5

    def score(self, ctx: MarketContext) -> float:
        return float(ctx.historical.edge_stability) * 0.5 + float(ctx.score_total) * 0.5

    def build_order_intent(self, ctx: MarketContext) -> OrderIntent | None:
        tid = ctx.candidate.primary_token_id()
        mid = ctx.live.book.mid() if ctx.live.book else None
        if not tid or mid is None:
            return None
        px = float(mid)
        notional = self._settings.max_order_size_usd * 0.3
        size = notional / max(px, 1e-6)
        return OrderIntent(
            market_id=ctx.candidate.market_id,
            token_id=tid,
            side=OrderSide.BUY,
            price=px,
            size=size,
            tif=TimeInForce.GTC,
        )
