"""Conservative fill simulation for backtests."""

from __future__ import annotations

from dataclasses import dataclass

from app.utils.math_utils import bps_to_fraction


@dataclass
class SimParams:
    fee_bps: float = 20.0
    slippage_bps: float = 10.0
    latency_bars: int = 0


def conservative_fill(
    side: str,
    price: float,
    size: float,
    mid: float,
    spread_bps: float,
    params: SimParams,
) -> tuple[float, float]:
    """Return (fill_price, fee_usd). Adverse slippage against direction."""
    slip = bps_to_fraction(params.slippage_bps + spread_bps * 0.5)
    if side.upper() == "BUY":
        fp = max(price, mid) * (1 + slip)
    else:
        fp = min(price, mid) * (1 - slip)
    notional = abs(fp * size)
    fee = notional * bps_to_fraction(params.fee_bps)
    return fp, fee
