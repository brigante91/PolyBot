"""Maker-first quoting: post-only limits, refresh, cancel/replace policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.clients.clob_client import ClobWrapper
from app.config import Settings
from app.logger import get_logger
from app.models.order import OrderIntent, OrderSide, TimeInForce

log = get_logger("quote_engine")


@dataclass
class QuoteState:
    order_id: str | None = None
    last_price: float = 0.0
    last_size: float = 0.0


class QuoteEngine:
    """
    Places post-only limits when live; adapts aggression from edge_net (caller supplies tier).
    edge_net high -> price closer to mid; low -> wider or skip.
    """

    def __init__(self, settings: Settings, clob: ClobWrapper) -> None:
        self._settings = settings
        self._clob = clob
        self._quotes: dict[str, QuoteState] = {}

    def prepare_intent(self, intent: OrderIntent, *, edge_net: float) -> OrderIntent | None:
        """Tier-adjust limit price; return None if edge too low to quote (maker-first)."""
        if edge_net < 0.01:
            log.info("quote_skipped_low_edge", edge_net=edge_net)
            return None
        adj = 0.0
        if edge_net > 0.05:
            adj = 0.002
        elif edge_net > 0.02:
            adj = 0.001
        new_price = max(
            0.01,
            min(0.99, intent.price + adj * (1 if intent.side == OrderSide.BUY else -1)),
        )
        return intent.model_copy(update={"price": new_price})

    def quote_limit(
        self,
        intent: OrderIntent,
        *,
        edge_net: float,
        post_only: bool | None = None,
    ) -> dict[str, Any]:
        po = self._settings.maker_first_post_only if post_only is None else post_only
        if not self._settings.enable_live_trading:
            log.info("quote_skipped_not_live", market_id=intent.market_id)
            return {}
        intent2 = self.prepare_intent(intent, edge_net=edge_net)
        if intent2 is None:
            return {}
        return self._clob.create_limit_order_post(intent2, post_only=po)

    def cancel_replace_key(self, market_key: str) -> None:
        self._quotes.pop(market_key, None)

    def register_sent(self, market_key: str, order_id: str, price: float, size: float) -> None:
        self._quotes[market_key] = QuoteState(order_id=order_id, last_price=price, last_size=size)
