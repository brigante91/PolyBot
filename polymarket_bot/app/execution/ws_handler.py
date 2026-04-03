"""Bridge WebSocket JSON events into typed book state + metrics for decision layer."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.logger import get_logger
from app.models.orderbook import BookLevel, OrderBookSnapshot

log = get_logger("ws_handler")


class WsMarketHub:
    """Thread-safe latest snapshot per asset_id from market channel."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._books: dict[str, OrderBookSnapshot] = {}
        self._event_count = 0
        self._last_event_at: float | None = None

    def apply_raw(self, msg: dict[str, Any]) -> None:
        et = msg.get("event_type") or msg.get("type")
        if et == "book":
            self._apply_book(msg)
        elif et == "best_bid_ask":
            self._apply_bba(msg)
        # price_change / last_trade_price: increment counters for metrics
        with self._lock:
            self._event_count += 1
            self._last_event_at = time.time()

    def _apply_book(self, msg: dict[str, Any]) -> None:
        aid = str(msg.get("asset_id", ""))
        if not aid:
            return
        bids = [BookLevel(price=float(x["price"]), size=float(x["size"])) for x in msg.get("bids") or []]
        asks = [BookLevel(price=float(x["price"]), size=float(x["size"])) for x in msg.get("asks") or []]
        snap = OrderBookSnapshot(token_id=aid, bids=bids, asks=asks)
        with self._lock:
            self._books[aid] = snap

    def _apply_bba(self, msg: dict[str, Any]) -> None:
        aid = str(msg.get("asset_id", ""))
        if not aid:
            return
        bb = float(msg["best_bid"]) if msg.get("best_bid") is not None else None
        ba = float(msg["best_ask"]) if msg.get("best_ask") is not None else None
        bids = [BookLevel(price=bb, size=0.0)] if bb is not None else []
        asks = [BookLevel(price=ba, size=0.0)] if ba is not None else []
        snap = OrderBookSnapshot(token_id=aid, bids=bids, asks=asks)
        with self._lock:
            self._books[aid] = snap

    def get_book(self, asset_id: str) -> OrderBookSnapshot | None:
        with self._lock:
            return self._books.get(asset_id)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "assets_tracked": len(self._books),
                "events": self._event_count,
                "last_event_at": self._last_event_at,
            }
