"""Shared HTTP: rate limit, retries, clock skew from Date header."""

from __future__ import annotations

import email.utils
import time
from collections.abc import Callable
from typing import Any, TypeVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from app.config import Settings

T = TypeVar("T")


class RateLimiter:
    """Simple token bucket (requests per second)."""

    def __init__(self, per_second: float) -> None:
        self._interval = 1.0 / max(per_second, 0.01)
        self._last = 0.0

    def acquire(self) -> None:
        now = time.monotonic()
        wait = self._last + self._interval - now
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()


class ClockSkewTracker:
    """Track server time vs local from HTTP Date header."""

    def __init__(self, max_skew_seconds: float) -> None:
        self.max_skew_seconds = max_skew_seconds
        self.last_skew: float | None = None
        self.last_warning: str | None = None

    def update_from_response(self, response: httpx.Response) -> None:
        date_hdr = response.headers.get("date")
        if not date_hdr:
            return
        try:
            server_dt = email.utils.parsedate_to_datetime(date_hdr)
            if server_dt.tzinfo is None:
                from datetime import timezone

                server_dt = server_dt.replace(tzinfo=timezone.utc)
            skew = abs(server_dt.timestamp() - time.time())
            self.last_skew = skew
            if skew > self.max_skew_seconds:
                self.last_warning = f"clock_skew_seconds={skew:.2f} exceeds max {self.max_skew_seconds}"
        except (TypeError, ValueError, OSError):
            self.last_warning = "could_not_parse_date_header"


def build_retry_decorator(settings: Settings) -> Callable[[Callable[..., T]], Callable[..., T]]:
    return retry(
        reraise=True,
        stop=stop_after_attempt(settings.http_max_retries),
        wait=wait_exponential_jitter(initial=0.5, max=30),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
    )


def should_retry_status(status: int) -> bool:
    return status == 429 or status >= 500
