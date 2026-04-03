"""Normalize and cache order book reads."""

from __future__ import annotations

from app.clients.clob_client import ClobWrapper
from app.models.orderbook import OrderBookSnapshot


class OrderbookService:
    def __init__(self, clob: ClobWrapper) -> None:
        self._clob = clob

    def snapshot(self, token_id: str) -> OrderBookSnapshot:
        return self._clob.get_order_book(token_id)
