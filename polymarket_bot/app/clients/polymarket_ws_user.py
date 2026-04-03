"""
Polymarket CLOB User WebSocket — orders, fills, trade status (authenticated).

Docs: wss://ws-subscriptions-clob.polymarket.com/ws/user
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

log = get_logger("ws_user")

DEFAULT_WS_USER = "wss://ws-subscriptions-clob.polymarket.com/ws/user"


class PolymarketWsUser:
    def __init__(
        self,
        settings: Settings,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        *,
        url: str | None = None,
        market_condition_ids: list[str] | None = None,
        on_reconnect: Callable[[], None] | None = None,
    ) -> None:
        self._settings = settings
        self._url = url or settings.ws_user_url or DEFAULT_WS_USER
        self._markets = market_condition_ids or []
        self._on_event = on_event or (lambda _e: None)
        self._on_reconnect = on_reconnect
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop = threading.Event()
        self._last_msg_at: float | None = None

    def start_background(self, market_condition_ids: list[str] | None = None) -> None:
        if market_condition_ids is not None:
            self._markets = market_condition_ids
        if not (self._settings.api_key and self._settings.api_secret and self._settings.api_passphrase):
            log.warning("ws_user_skip_no_credentials")
            return

        self._stop.clear()

        def _run() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._runner())

        self._thread = threading.Thread(target=_run, name="poly-ws-user", daemon=True)
        self._thread.start()

    async def _runner(self) -> None:
        import websockets

        payload = {
            "auth": {
                "apiKey": self._settings.api_key,
                "secret": self._settings.api_secret,
                "passphrase": self._settings.api_passphrase,
            },
            "markets": self._markets,
            "type": "user",
        }
        backoff = 1.0
        while not self._stop.is_set():
            try:
                async with websockets.connect(
                    self._url,
                    ping_interval=10,
                    ping_timeout=20,
                    close_timeout=5,
                    max_size=10_000_000,
                ) as ws:
                    await ws.send(json.dumps(payload))
                    log.info("ws_user_subscribed", markets=len(self._markets))
                    backoff = 1.0
                    async for raw in ws:
                        if self._stop.is_set():
                            break
                        self._last_msg_at = time.time()
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(msg, dict):
                            self._on_event(msg)
            except Exception as e:
                log.warning("ws_user_reconnect", error=str(e), backoff=backoff)
                if self._on_reconnect:
                    try:
                        self._on_reconnect()
                    except Exception:
                        pass
                await asyncio.sleep(backoff)
                backoff = min(60.0, backoff * 2.0)

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
