"""Simple TTL cache for REST responses."""

from __future__ import annotations

import time
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float = 2.0) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        item = self._data.get(key)
        if not item:
            return None
        ts, val = item
        if time.time() - ts > self._ttl:
            del self._data[key]
            return None
        return val

    def set(self, key: str, value: T) -> None:
        self._data[key] = (time.time(), value)
