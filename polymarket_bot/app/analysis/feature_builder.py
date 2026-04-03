"""Combine raw signals into feature vectors for scoring / ML hooks."""

from __future__ import annotations

from app.models.context import LiveFeatures


def normalize_imbalance(bid_sz: float, ask_sz: float) -> float:
    tot = bid_sz + ask_sz
    if tot <= 0:
        return 0.0
    return (bid_sz - ask_sz) / tot
