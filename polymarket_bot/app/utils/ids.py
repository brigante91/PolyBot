"""Idempotency and client order id helpers."""

from __future__ import annotations

import hashlib
import uuid


def new_idempotency_key(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex}"


def stable_hash(parts: tuple[str, ...]) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode())
    return h.hexdigest()[:32]
