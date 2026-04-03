"""Time helpers."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(dt: str | None) -> datetime | None:
    if not dt:
        return None
    try:
        if dt.endswith("Z"):
            dt = dt.replace("Z", "+00:00")
        return datetime.fromisoformat(dt)
    except ValueError:
        return None


def age_seconds(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return (utc_now() - dt.replace(tzinfo=dt.tzinfo or timezone.utc)).total_seconds()
