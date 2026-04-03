"""Aggregate market data: order book + midpoint + optional last trade."""

from __future__ import annotations

from app.clients.clob_client import ClobWrapper
from app.models.orderbook import OrderBookSnapshot


class MarketDataService:
    def __init__(self, clob: ClobWrapper) -> None:
        self._clob = clob

    def full_quote(self, token_id: str) -> tuple[OrderBookSnapshot, float | None, float | None]:
        book = self._clob.get_order_book(token_id)
        mid = self._clob.get_midpoint(token_id)
        last = self._clob.get_last_trade_price(token_id)
        return book, mid, last
