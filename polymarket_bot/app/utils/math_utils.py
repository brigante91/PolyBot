"""Math helpers."""

from __future__ import annotations


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def bps_to_fraction(bps: float) -> float:
    return bps / 10000.0
