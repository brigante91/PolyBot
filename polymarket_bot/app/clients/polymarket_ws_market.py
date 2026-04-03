"""
Polymarket CLOB Market WebSocket — order book, price changes, trades.

Docs: wss://ws-subscriptions-clob.polymarket.com/ws/market
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import Callable
from typing import Any

from app.config import Settings
from app.logger import get_logger

log = get_logger("ws_market")

DEFAULT_WS_MARKET = "wss://ws-subscriptions-clob.polymarket.com/ws/market"


class PolymarketWsMarket:
    """
    Async WS client with optional background thread for sync code.
    Callback receives parsed JSON dicts (raw payload).
    """

    def __init__(
        self,
        settings: Settings,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        *,
        url: str | None = None,
        on_reconnect: Callable[[], None] | None = None,
    ) -> None:
        self._settings = settings
        self._url = url or settings.ws_market_url or DEFAULT_WS_MARKET
        self._on_event = on_event or (lambda _e: None)
        self._on_reconnect = on_reconnect
        self._task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._assets: list[str] = []
        self._last_msg_at: float | None = None
        self._latency_ms: float | None = None

    @property
    def latency_ms(self) -> float | None:
        return self._latency_ms

    @property
    def last_msg_at(self) -> float | None:
        return self._last_msg_at

    def start_background(self, asset_ids: list[str]) -> None:
        """Run asyncio loop in a daemon thread."""
        self._assets = asset_ids
        self._stop.clear()

        def _run() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._runner())

        self._thread = threading.Thread(target=_run, name="poly-ws-market", daemon=True)
        self._thread.start()

    async def run_forever(self, asset_ids: list[str]) -> None:
        """Async entry: await inside existing loop."""
        self._assets = asset_ids
        await self._runner()

    async def _runner(self) -> None:
        import websockets

        sub = {
            "assets_ids": self._assets,
            "type": "market",
            "custom_feature_enabled": True,
        }
        backoff = 1.0
        while not self._stop.is_set():
            t0 = time.perf_counter()
            try:
                async with websockets.connect(
                    self._url,
                    ping_interval=10,
                    ping_timeout=20,
                    close_timeout=5,
                    max_size=10_000_000,
                ) as ws:
                    await ws.send(json.dumps(sub))
                    log.info("ws_market_subscribed", n=len(self._assets))
                    backoff = 1.0
                    async for raw in ws:
                        if self._stop.is_set():
                            break
                        self._last_msg_at = time.time()
                        self._latency_ms = (time.perf_counter() - t0) * 1000.0
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(msg, dict):
                            self._on_event(msg)
            except Exception as e:
                log.warning("ws_market_reconnect", error=str(e), backoff=backoff)
                if self._on_reconnect:
                    try:
                        self._on_reconnect()
                    except Exception:
                        pass
                await asyncio.sleep(backoff)
                backoff = min(60.0, backoff * 2.0)

    def stop(self) -> None:
        self._stop.set()
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(asyncio.sleep(0), self._loop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
