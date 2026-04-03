"""
Fair value engine: estimate P(YES at expiry) vs market-implied prob from the book.

Uses a blend of:
- structural digital/binary proxy when underlying + strike + time + vol are available;
- microstructure adjustment from imbalance, momentum, distance from mid.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.utils.math_utils import bps_to_fraction


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-50.0, min(50.0, x))))


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass
class FairValueInputs:
    """market_mid is implied P(up) from CLOB mid for the YES token."""

    market_mid: float
    underlying_price: float | None = None
    price_to_beat: float | None = None
    time_to_expiry_years: float = 1e-6
    price_velocity: float = 0.0
    volatility_annual: float = 0.5
    book_imbalance: float = 0.0
    distance_from_mid_bps: float = 0.0


@dataclass
class FairValueResult:
    fair_prob: float
    market_prob: float
    edge: float
    edge_net: float
    confidence: float


class FairValueEngine:
    """
    Outputs fair_prob in (0,1), compares to market_mid, subtracts fee/slippage buffer for edge_net.
    """

    def __init__(self, fee_bps: float = 20.0, slippage_bps: float = 10.0) -> None:
        self._fee = bps_to_fraction(fee_bps)
        self._slip = bps_to_fraction(slippage_bps)

    def estimate(self, inp: FairValueInputs) -> FairValueResult:
        m = max(0.01, min(0.99, float(inp.market_mid)))
        structural: float | None = None
        s, k = inp.underlying_price, inp.price_to_beat
        if s is not None and k is not None and s > 0 and k > 0 and inp.time_to_expiry_years > 0:
            vol = max(0.05, float(inp.volatility_annual))
            t = max(1e-10, float(inp.time_to_expiry_years))
            # Log-moneyness rough digital probability (risk-neutral style proxy, not a pricing model).
            ln_sk = math.log(s / k)
            scale = vol * math.sqrt(t)
            z = ln_sk / scale if scale > 1e-12 else 0.0
            structural = _norm_cdf(z)

        micro = (
            0.55 * inp.book_imbalance
            + 0.25 * max(-1.0, min(1.0, inp.price_velocity * 50.0))
            - 0.15 * max(-1.0, min(1.0, inp.distance_from_mid_bps / 200.0))
        )
        heuristic = _sigmoid(2.0 * (m - 0.5) + micro)

        if structural is not None:
            fair = 0.55 * structural + 0.45 * heuristic
        else:
            fair = 0.35 * m + 0.65 * heuristic

        fair = max(0.02, min(0.98, fair))
        edge = fair - m
        costs = self._fee + self._slip
        edge_net = edge - costs

        vol = float(inp.volatility_annual)
        conf_parts = [
            0.35 * (1.0 - min(1.0, abs(vol) / 2.0)) if structural is not None else 0.2,
            0.35 * (1.0 - min(1.0, abs(inp.book_imbalance))),
            0.30 * (1.0 - min(1.0, abs(inp.distance_from_mid_bps) / 400.0)),
        ]
        confidence = max(0.1, min(0.95, sum(conf_parts)))

        return FairValueResult(
            fair_prob=fair,
            market_prob=m,
            edge=edge,
            edge_net=edge_net,
            confidence=confidence,
        )
