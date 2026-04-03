"""Order lifecycle for advanced reconciliation."""

from __future__ import annotations

from enum import Enum


class OrderLifecycle(str, Enum):
    INTENT = "intent"
    SENT = "sent"
    ACK = "ack"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    UNKNOWN = "unknown"
