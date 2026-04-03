"""Helpers for tags/categories from Gamma raw payloads."""

from __future__ import annotations

from typing import Any


def infer_category(raw: dict[str, Any]) -> str | None:
    ev = raw.get("events")
    if isinstance(ev, list) and ev:
        first = ev[0]
        if isinstance(first, dict):
            return first.get("title") or first.get("slug")
    return raw.get("category")
