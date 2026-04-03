"""
Production-grade realtime state engine for PolyBot.

Goals:
- single in-memory source of truth for order books, user orders, fills, and health
- tolerate mixed websocket payloads by normalizing events before persistence
- expose thread-safe snapshots for orchestrator, risk engine, and TUI
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.models.orderbook import BookLevel, OrderBookSnapshot

if TYPE_CHECKING:
    from app.config import Settings


@dataclass(slots=True)
class FeedHealth:
    ok: bool = True
    last_event_ts: float = 0.0
    last_error: str | None = None
    reconnect_count: int = 0

    def mark_ok(self) -> None:
        self.ok = True
        self.last_event_ts = time.time()
        self.last_error = None

    def mark_error(self, detail: str) -> None:
        self.ok = False
        self.last_error = detail
        self.last_event_ts = time.time()

    def bump_reconnect(self) -> None:
        self.reconnect_count += 1
        self.last_event_ts = time.time()


@dataclass(slots=True)
class BookState:
    asset_id: str
    book: OrderBookSnapshot | None = None
    last_event_ts: float = 0.0
    sequence: int | None = None
    stale: bool = True
    source: str = "unknown"


class RealtimeStateEngine:
    """
    Thread-safe runtime state.

    Notes:
    - `apply_market_event()` accepts raw websocket payloads and tries to normalize them.
    - `apply_user_event()` accepts raw user websocket payloads and stores normalized rows.
    - `snapshot()` returns compact state for TUI / metrics.
    """

    def __init__(self, *, stale_after_seconds: float = 15.0, keep_recent: int = 500) -> None:
        self._lock = threading.RLock()
        self._stale_after = float(stale_after_seconds)

        self._books: dict[str, BookState] = {}
        self._user_orders: dict[str, dict[str, Any]] = {}
        self._recent_fills: deque[dict[str, Any]] = deque(maxlen=keep_recent)
        self._recent_trades: deque[dict[str, Any]] = deque(maxlen=keep_recent)
        self._recent_market_events: deque[dict[str, Any]] = deque(maxlen=keep_recent)
        self._recent_user_events: deque[dict[str, Any]] = deque(maxlen=keep_recent)

        self._feed_market = FeedHealth()
        self._feed_user = FeedHealth()

    # ---------------------------
    # Public low-level methods
    # ---------------------------

    def mark_stale(self, asset_id: str) -> None:
        with self._lock:
            state = self._books.setdefault(asset_id, BookState(asset_id=asset_id))
            state.stale = True

    def clear_stale(self, asset_id: str) -> None:
        with self._lock:
            state = self._books.setdefault(asset_id, BookState(asset_id=asset_id))
            state.stale = False
            state.last_event_ts = time.time()

    def is_stale(self, asset_id: str) -> bool:
        with self._lock:
            state = self._books.get(asset_id)
            if state is None:
                return True
            if state.stale:
                return True
            return (time.time() - state.last_event_ts) > self._stale_after

    def get_book(self, asset_id: str) -> OrderBookSnapshot | None:
        with self._lock:
            state = self._books.get(asset_id)
            return state.book if state else None

    def apply_book_snapshot(
        self,
        asset_id: str,
        book: OrderBookSnapshot,
        *,
        sequence: int | None = None,
        source: str = "snapshot",
    ) -> None:
        with self._lock:
            state = self._books.setdefault(asset_id, BookState(asset_id=asset_id))
            state.book = book
            state.sequence = sequence
            state.source = source
            state.last_event_ts = time.time()
            state.stale = False
            self._feed_market.mark_ok()
            self._recent_market_events.append(
                {
                    "kind": "book_snapshot",
                    "asset_id": asset_id,
                    "sequence": sequence,
                    "best_bid": book.best_bid,
                    "best_ask": book.best_ask,
                    "ts": state.last_event_ts,
                }
            )

    def apply_user_order(self, order_id: str, row: dict[str, Any]) -> None:
        with self._lock:
            self._user_orders[order_id] = dict(row)
            self._feed_user.mark_ok()
            self._recent_user_events.append(
                {"kind": "order", "order_id": order_id, "status": row.get("status"), "ts": time.time()}
            )

    def apply_fill(self, row: dict[str, Any]) -> None:
        with self._lock:
            self._recent_fills.append(dict(row))
            self._feed_user.mark_ok()
            self._recent_user_events.append({"kind": "fill", "row": dict(row), "ts": time.time()})

    def apply_trade(self, row: dict[str, Any]) -> None:
        with self._lock:
            self._recent_trades.append(dict(row))
            self._feed_market.mark_ok()
            self._recent_market_events.append({"kind": "trade", "row": dict(row), "ts": time.time()})

    def set_ws_health(self, *, market_ok: bool | None = None, user_ok: bool | None = None, detail: str | None = None) -> None:
        with self._lock:
            if market_ok is not None:
                if market_ok:
                    self._feed_market.mark_ok()
                else:
                    self._feed_market.mark_error(detail or "market_ws_error")
            if user_ok is not None:
                if user_ok:
                    self._feed_user.mark_ok()
                else:
                    self._feed_user.mark_error(detail or "user_ws_error")

    def bump_reconnect(self, *, feed: str) -> None:
        with self._lock:
            if feed == "market":
                self._feed_market.bump_reconnect()
            elif feed == "user":
                self._feed_user.bump_reconnect()

    # ---------------------------
    # Normalizers for raw WS data
    # ---------------------------

    def apply_market_event(self, payload: dict[str, Any]) -> None:
        """
        Accept raw market websocket payloads.

        Supports common shapes:
        - snapshot / book with bids/asks/token_id or asset_id
        - trade rows
        - top-of-book style updates
        """
        if not isinstance(payload, dict):
            return

        asset_id = str(payload.get("asset_id") or payload.get("token_id") or payload.get("market") or "")
        event_type = str(payload.get("type") or payload.get("event_type") or payload.get("channel") or "").lower()
        sequence = payload.get("seq") or payload.get("sequence")

        # Trade-like payload
        if event_type in {"trade", "last_trade"} or ("price" in payload and "size" in payload and not payload.get("bids")):
            row = {
                "asset_id": asset_id,
                "price": _to_float(payload.get("price")),
                "size": _to_float(payload.get("size")),
                "side": payload.get("side"),
                "trade_id": payload.get("trade_id") or payload.get("id"),
                "ts": payload.get("timestamp") or time.time(),
            }
            self.apply_trade(row)
            return

        bids = payload.get("bids") or payload.get("buy") or []
        asks = payload.get("asks") or payload.get("sell") or []

        if asset_id and (bids or asks):
            book = OrderBookSnapshot(
                token_id=asset_id,
                bids=_parse_levels(bids),
                asks=_parse_levels(asks),
            )
            self.apply_book_snapshot(asset_id, book, sequence=sequence, source=event_type or "market_event")
            return

        # Top of book only
        best_bid = payload.get("best_bid")
        best_ask = payload.get("best_ask")
        if asset_id and (best_bid is not None or best_ask is not None):
            prev = self.get_book(asset_id)
            bids = prev.bids if prev else []
            asks = prev.asks if prev else []
            if best_bid is not None:
                bids = [BookLevel(price=float(best_bid), size=float(payload.get("best_bid_size") or 0.0))]
            if best_ask is not None:
                asks = [BookLevel(price=float(best_ask), size=float(payload.get("best_ask_size") or 0.0))]
            book = OrderBookSnapshot(token_id=asset_id, bids=bids, asks=asks)
            self.apply_book_snapshot(asset_id, book, sequence=sequence, source="top_of_book")
            return

        with self._lock:
            self._recent_market_events.append({"kind": "unknown_market_event", "payload": payload, "ts": time.time()})

    def apply_user_event(self, payload: dict[str, Any]) -> None:
        """
        Accept raw user websocket payloads.

        Supports common shapes:
        - order updates
        - fill updates
        - cancel / reject events
        """
        if not isinstance(payload, dict):
            return

        event_type = str(payload.get("type") or payload.get("event_type") or "").lower()
        order_id = str(payload.get("order_id") or payload.get("id") or payload.get("client_order_id") or "")

        if event_type in {"fill", "match", "trade"} or payload.get("filled_size") or payload.get("fill_price"):
            self.apply_fill(
                {
                    "order_id": order_id,
                    "market_id": payload.get("market_id"),
                    "asset_id": payload.get("asset_id") or payload.get("token_id"),
                    "side": payload.get("side"),
                    "price": _to_float(payload.get("fill_price") or payload.get("price")),
                    "size": _to_float(payload.get("filled_size") or payload.get("size")),
                    "status": payload.get("status") or "filled",
                    "ts": payload.get("timestamp") or time.time(),
                }
            )
            return

        if order_id:
            row = {
                "order_id": order_id,
                "client_order_id": payload.get("client_order_id"),
                "market_id": payload.get("market_id"),
                "asset_id": payload.get("asset_id") or payload.get("token_id"),
                "side": payload.get("side"),
                "price": _to_float(payload.get("price")),
                "size": _to_float(payload.get("size")),
                "remaining_size": _to_float(payload.get("remaining_size")),
                "status": payload.get("status") or event_type or "open",
                "post_only": bool(payload.get("post_only", False)),
                "ts": payload.get("timestamp") or time.time(),
            }
            self.apply_user_order(order_id, row)
            return

        with self._lock:
            self._recent_user_events.append({"kind": "unknown_user_event", "payload": payload, "ts": time.time()})

    # ---------------------------
    # Snapshots for TUI / metrics
    # ---------------------------

    def is_user_feed_degraded(self, settings: "Settings", *, max_silence_seconds: float = 90.0) -> bool:
        """Live user channel expected but no healthy traffic for too long."""
        if not settings.enable_ws:
            return False
        if not (settings.api_key and settings.api_secret and settings.api_passphrase):
            return False
        with self._lock:
            if not self._feed_user.ok:
                return True
            ts = self._feed_user.last_event_ts
            if ts <= 0:
                return False
            return (time.time() - ts) > max_silence_seconds

    def request_resync_asset(self, asset_id: str, *, reason: str = "incoherent") -> None:
        """Mark stale and record intent — REST refresh should be done by orchestrator."""
        self.mark_stale(asset_id)
        with self._lock:
            self._recent_market_events.append(
                {"kind": "resync_request", "asset_id": asset_id, "reason": reason, "ts": time.time()}
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            books_summary: list[dict[str, Any]] = []
            now = time.time()
            for asset_id, state in self._books.items():
                book = state.book
                books_summary.append(
                    {
                        "asset_id": asset_id,
                        "best_bid": book.best_bid if book else None,
                        "best_ask": book.best_ask if book else None,
                        "mid": book.mid() if book else None,
                        "spread_bps": book.spread_bps() if book else None,
                        "stale": state.stale or ((now - state.last_event_ts) > self._stale_after),
                        "sequence": state.sequence,
                        "source": state.source,
                        "updated_at": state.last_event_ts,
                    }
                )

            return {
                "books": books_summary,
                "open_user_orders": list(self._user_orders.values()),
                "recent_fills": list(self._recent_fills)[-50:],
                "recent_trades": list(self._recent_trades)[-50:],
                "recent_market_events": list(self._recent_market_events)[-50:],
                "recent_user_events": list(self._recent_user_events)[-50:],
                "feeds": {
                    "market_ok": self._feed_market.ok,
                    "market_last_event_ts": self._feed_market.last_event_ts,
                    "market_last_error": self._feed_market.last_error,
                    "market_reconnect_count": self._feed_market.reconnect_count,
                    "user_ok": self._feed_user.ok,
                    "user_last_event_ts": self._feed_user.last_event_ts,
                    "user_last_error": self._feed_user.last_error,
                    "user_reconnect_count": self._feed_user.reconnect_count,
                },
            }


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_levels(levels: list[Any]) -> list[BookLevel]:
    parsed: list[BookLevel] = []
    for row in levels:
        if isinstance(row, dict):
            price = _to_float(row.get("price"))
            size = _to_float(row.get("size"))
        elif isinstance(row, (list, tuple)) and len(row) >= 2:
            price = _to_float(row[0])
            size = _to_float(row[1])
        else:
            continue
        if price is None or size is None:
            continue
        parsed.append(BookLevel(price=price, size=size))
    return parsed
