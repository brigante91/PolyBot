"""Conservative position sizing: bps of bankroll, volatility/spread scaling, hard caps."""

from __future__ import annotations

from app.config import Settings
from app.utils.math_utils import bps_to_fraction, clamp


class PositionSizer:
    """
    Risk per trade in bps of bankroll (config range), scaled down when spread is wide.
    No martingale: size does not increase after losses.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def size_usd(
        self,
        *,
        bankroll_usd: float,
        confidence: float,
        spread_bps: float | None,
        mid_price: float | None,
    ) -> float:
        low = self._settings.risk_per_trade_bps_min
        high = self._settings.risk_per_trade_bps_max
        bps = low + (high - low) * clamp(confidence, 0.0, 1.0)
        if spread_bps is not None and spread_bps > 0:
            # Widen spread => reduce size (linear dampening above half max spread setting)
            threshold = self._settings.max_spread_bps * 0.5
            if spread_bps > threshold:
                factor = clamp(threshold / spread_bps, 0.2, 1.0)
                bps *= factor
        risk_usd = bankroll_usd * bps_to_fraction(bps)
        risk_usd = min(risk_usd, self._settings.max_order_size_usd)
        if mid_price and mid_price > 0:
            # optional: notional in shares — here we stay in USD notional cap
            pass
        return max(0.0, risk_usd)
