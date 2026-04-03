"""
Thread-safe in-memory view of books, user orders, and recent fills.

Wire market/user WebSocket callbacks into `apply_market_event` / `apply_user_event`.
When feeds are stale, call `mark_stale` / `clear_stale` from the orchestrator.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from app.models.orderbook import OrderBookSnapshot


class RealtimeStateEngine:
    def __init__(self, *, stale_after_seconds: float = 15.0) -> None:
        self._lock = threading.RLock()
        self._stale_after = stale_after_seconds
        self._books: dict[str, OrderBookSnapshot] = {}
        self._book_updated_at: dict[str, float] = {}
        self._stale_markets: set[str] = set()
        self._user_orders: dict[str, dict[str, Any]] = {}
        self._recent_fills: deque[dict[str, Any]] = deque(maxlen=500)
        self._recent_trades: deque[dict[str, Any]] = deque(maxlen=500)
        self._ws_market_ok = True
        self._ws_user_ok = True
        self._reconnect_count = 0

    def mark_stale(self, asset_id: str) -> None:
        with self._lock:
            self._stale_markets.add(asset_id)

    def clear_stale(self, asset_id: str) -> None:
        with self._lock:
            self._stale_markets.discard(asset_id)

    def is_stale(self, asset_id: str) -> bool:
        with self._lock:
            if asset_id in self._stale_markets:
                return True
            t = self._book_updated_at.get(asset_id)
            if t is None:
                return True
            return (time.time() - t) > self._stale_after

    def apply_book_snapshot(self, asset_id: str, book: OrderBookSnapshot) -> None:
        with self._lock:
            self._books[asset_id] = book
            self._book_updated_at[asset_id] = time.time()
            self._stale_markets.discard(asset_id)

    def get_book(self, asset_id: str) -> OrderBookSnapshot | None:
        with self._lock:
            return self._books.get(asset_id)

    def apply_user_order(self, order_id: str, row: dict[str, Any]) -> None:
        with self._lock:
            self._user_orders[order_id] = row

    def apply_fill(self, row: dict[str, Any]) -> None:
        with self._lock:
            self._recent_fills.append(row)

    def apply_trade(self, row: dict[str, Any]) -> None:
        with self._lock:
            self._recent_trades.append(row)

    def set_ws_health(self, *, market_ok: bool | None = None, user_ok: bool | None = None) -> None:
        with self._lock:
            if market_ok is not None:
                self._ws_market_ok = market_ok
            if user_ok is not None:
                self._ws_user_ok = user_ok

    def bump_reconnect(self) -> None:
        with self._lock:
            self._reconnect_count += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "assets_tracked": len(self._books),
                "stale_assets": list(self._stale_markets),
                "open_user_orders": len(self._user_orders),
                "recent_fills": list(self._recent_fills)[-20:],
                "ws_market_ok": self._ws_market_ok,
                "ws_user_ok": self._ws_user_ok,
                "reconnect_count": self._reconnect_count,
            }
