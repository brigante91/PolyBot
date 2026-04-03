"""Data API client (positions, trades, activity). Paths documented in Polymarket docs."""

from __future__ import annotations

from typing import Any

import httpx

from app.clients.http_common import ClockSkewTracker, RateLimiter, should_retry_status
from app.config import Settings


class DataApiClient:
    """
    Public Data API — no auth for read endpoints.
    Base URL configurable via DATA_API_BASE (default https://data-api.polymarket.com).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base = settings.data_api_base.rstrip("/")
        self._rl = RateLimiter(settings.rate_limit_per_second)
        self._clock = ClockSkewTracker(settings.clock_skew_max_seconds)
        self._client = httpx.Client(timeout=settings.http_timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        self._rl.acquire()
        url = f"{self._base}{path}"
        attempt = 0
        while True:
            attempt += 1
            resp = self._client.get(url, params=params)
            self._clock.update_from_response(resp)
            if should_retry_status(resp.status_code) and attempt < self._settings.http_max_retries:
                import time

                time.sleep(min(2**attempt * 0.2, 30))
                continue
            resp.raise_for_status()
            return resp.json()

    def get_positions(self, user_address: str, **kwargs: Any) -> list[dict[str, Any]]:
        """GET /positions — current positions for wallet."""
        params: dict[str, Any] = {"user": user_address, **kwargs}
        data = self._get("/positions", params)
        return data if isinstance(data, list) else []

    def get_trades(self, user_address: str, **kwargs: Any) -> list[dict[str, Any]]:
        """GET /trades — user trades (see official docs for filters)."""
        params: dict[str, Any] = {"user": user_address, **kwargs}
        data = self._get("/trades", params)
        return data if isinstance(data, list) else []

    def get_activity(self, user_address: str, **kwargs: Any) -> list[dict[str, Any]]:
        """GET /activity — user activity feed."""
        params: dict[str, Any] = {"user": user_address, **kwargs}
        data = self._get("/activity", params)
        return data if isinstance(data, list) else []

    @property
    def clock_skew_warning(self) -> str | None:
        return self._clock.last_warning
