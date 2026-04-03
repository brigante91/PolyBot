"""
REST fallback for underlying spot prices (BTC/ETH/SOL) when RTDS is not configured.

RTDS can replace this later with a streaming client; same FairValueInputs fields apply.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.logger import get_logger

log = get_logger("spot_price")

# Binance public ticker (no key) — for probabilistic FV inputs only, not execution prices.
_BINANCE_SYMBOL = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}


class SpotPriceClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.Client(timeout=float(settings.http_timeout_seconds))

    def close(self) -> None:
        self._client.close()

    def fetch_usd(self, symbol: str) -> float | None:
        """symbol is BTC / ETH / SOL."""
        pair = _BINANCE_SYMBOL.get(symbol.upper())
        if not pair:
            return None
        if not self._settings.enable_spot_price_rest:
            return None
        try:
            r = self._client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": pair},
            )
            r.raise_for_status()
            data: dict[str, Any] = r.json()
            return float(data["price"])
        except Exception as e:
            log.debug("spot_price_fetch_failed", extra={"symbol": symbol, "error": str(e)})
            return None
