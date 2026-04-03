"""Simulated fills from bid/ask with fee and slippage (conservative)."""

from __future__ import annotations

import uuid
from typing import Any

from app.config import Settings
from app.models.order import OrderIntent, OrderSide
from app.models.orderbook import OrderBookSnapshot
from app.utils.ids import new_idempotency_key
from app.utils.math_utils import bps_to_fraction


class PaperBroker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def simulate_fill(self, intent: OrderIntent, book: OrderBookSnapshot | None) -> dict[str, Any]:
        """
        Conservative fill: cross the spread with extra slippage bps and fee.
        Queue: optional size haircut from assumed queue ahead (reduces effective fill).
        """
        fee_bps = self._settings.paper_fee_bps
        slip_bps = self._settings.paper_slippage_bps
        queue = self._settings.paper_assumed_queue_ahead

        fill_price = float(intent.price)
        fill_size = float(intent.size)

        if book:
            bb, ba = book.best_bid, book.best_ask
            if intent.side == OrderSide.BUY and ba is not None:
                fill_price = max(fill_price, float(ba)) * (1 + bps_to_fraction(slip_bps))
            elif intent.side == OrderSide.SELL and bb is not None:
                fill_price = min(fill_price, float(bb)) * (1 - bps_to_fraction(slip_bps))

        effective = max(fill_size - queue, 0.0)
        if effective <= 0:
            effective = fill_size * 0.1

        notional = effective * fill_price
        fee = notional * bps_to_fraction(fee_bps)

        return {
            "order_id": new_idempotency_key("paper-"),
            "client_order_id": intent.client_order_id or str(uuid.uuid4()),
            "fill_price": fill_price,
            "fill_size": effective,
            "fee_usd": fee,
            "mode": "paper",
        }
