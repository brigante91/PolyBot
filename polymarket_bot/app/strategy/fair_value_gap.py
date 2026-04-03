from __future__ import annotations

from app.analysis.fair_value_engine import FairValueResult
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
        fv = ctx.fair_value
        if fv is None:
            return False
        if fv.confidence < 0.35:
            return False
        costs = bps_to_fraction(self._settings.max_spread_bps) + bps_to_fraction(self._settings.paper_fee_bps)
        return abs(fv.edge_net) > costs * 1.25

    def score(self, ctx: MarketContext) -> float:
        fv = ctx.fair_value
        if fv is None:
            return 0.0
        edge_term = min(1.0, abs(fv.edge_net) * 15.0)
        return float(fv.confidence) * edge_term * 0.55 + float(ctx.historical.edge_stability) * 0.2 + float(ctx.score_total) * 0.25

    def build_order_intent(self, ctx: MarketContext) -> OrderIntent | None:
        fv = ctx.fair_value
        tid = ctx.candidate.primary_token_id()
        mid = ctx.live.book.mid() if ctx.live.book else None
        if not tid or mid is None or fv is None:
            return None
        side = OrderSide.BUY if fv.fair_prob >= fv.market_prob else OrderSide.SELL
        px = float(mid)
        notional = self._settings.max_order_size_usd * 0.3 * max(0.5, fv.confidence)
        size = notional / max(px, 1e-6)
        return OrderIntent(
            market_id=ctx.candidate.market_id,
            token_id=tid,
            side=side,
            price=px,
            size=size,
            tif=TimeInForce.GTC,
        )
