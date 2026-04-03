"""Gamma API client for market discovery.

Example (public):

    from app.config import load_settings
    from app.clients.gamma_client import GammaClient

    g = GammaClient(load_settings())
    markets = g.fetch_markets_page(active=True, closed=False, limit=5)
    print(markets[0].clob_token_ids)
    g.close()
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.clients.http_common import ClockSkewTracker, RateLimiter, should_retry_status
from app.config import Settings
from app.models.market import GammaMarket
from app.utils.time import parse_iso


def _parse_json_field(val: Any) -> Any:
    if isinstance(val, str) and (val.startswith("[") or val.startswith("{")):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return val
    return val


class GammaClient:
    """Fetch markets from Gamma API (public)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._rl = RateLimiter(settings.rate_limit_per_second)
        self._clock = ClockSkewTracker(settings.clock_skew_max_seconds)
        self._client = httpx.Client(timeout=settings.http_timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def fetch_markets_page(
        self,
        *,
        active: bool = True,
        closed: bool = False,
        limit: int = 50,
        offset: int = 0,
        order: str | None = None,
        ascending: bool = False,
    ) -> list[GammaMarket]:
        """GET /markets with pagination."""
        self._rl.acquire()
        params: dict[str, Any] = {
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
            "ascending": str(ascending).lower(),
        }
        if order:
            params["order"] = order
        url = f"{self._settings.gamma_host.rstrip('/')}/markets"
        attempt = 0
        while True:
            attempt += 1
            resp = self._client.get(url, params=params)
            self._clock.update_from_response(resp)
            if should_retry_status(resp.status_code) and attempt < self._settings.http_max_retries:
                import time

                time.sleep(min(2**attempt * 0.2, 30))
                continue
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                return []
            return [self._normalize(m) for m in data]

    def fetch_market_by_id(self, market_id: str) -> GammaMarket | None:
        self._rl.acquire()
        url = f"{self._settings.gamma_host.rstrip('/')}/markets/{market_id}"
        resp = self._client.get(url)
        self._clock.update_from_response(resp)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._normalize(resp.json())

    def fetch_all_active_markets(self, max_pages: int = 100) -> list[GammaMarket]:
        """Paginate until empty or max_pages."""
        out: list[GammaMarket] = []
        offset = 0
        limit = 100
        for _ in range(max_pages):
            page = self.fetch_markets_page(active=True, closed=False, limit=limit, offset=offset)
            if not page:
                break
            out.extend(page)
            if len(page) < limit:
                break
            offset += limit
        return out

    def _normalize(self, raw: dict[str, Any]) -> GammaMarket:
        clob_raw = _parse_json_field(raw.get("clobTokenIds"))
        if isinstance(clob_raw, list):
            clob_ids = [str(x) for x in clob_raw]
        else:
            clob_ids = []
        outcomes_raw = _parse_json_field(raw.get("outcomes"))
        outcomes: list[str] | None = None
        if isinstance(outcomes_raw, list):
            outcomes = [str(x) for x in outcomes_raw]

        end = parse_iso(raw.get("endDateIso")) or parse_iso(raw.get("endDate"))

        liq = raw.get("liquidityNum")
        if liq is None and raw.get("liquidity") is not None:
            try:
                liq = float(raw["liquidity"])
            except (TypeError, ValueError):
                liq = None

        vol24 = raw.get("volume24hr")
        if vol24 is None:
            vol24 = raw.get("volume24hrClob")

        return GammaMarket(
            id=str(raw.get("id", "")),
            slug=raw.get("slug"),
            question=raw.get("question"),
            active=bool(raw.get("active", True)),
            closed=bool(raw.get("closed", False)),
            liquidity_num=float(liq) if liq is not None else None,
            volume_24hr=float(vol24) if vol24 is not None else None,
            end_date=end,
            clob_token_ids=clob_ids,
            outcomes=outcomes,
            tick_size=str(raw.get("orderPriceMinTickSize")) if raw.get("orderPriceMinTickSize") else None,
            raw=raw,
        )

    @property
    def clock_skew_warning(self) -> str | None:
        return self._clock.last_warning

    @property
    def last_clock_skew_seconds(self) -> float | None:
        return self._clock.last_skew
