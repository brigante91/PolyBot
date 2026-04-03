"""Thin wrapper around py-clob-client with typed helpers.

Example — read-only order book:

    from app.config import load_settings
    from app.clients.clob_client import ClobWrapper

    c = ClobWrapper(load_settings())
    book = c.get_order_book("<token_id>")
    print(book.best_bid, book.best_ask)

Example — limit BUY intent (live only with credentials + ENABLE_LIVE_TRADING):

    from app.models.order import OrderIntent, OrderSide, TimeInForce

    intent = OrderIntent(
        market_id="m",
        token_id="<token_id>",
        side=OrderSide.BUY,
        price=0.45,
        size=10.0,
        tif=TimeInForce.GTC,
    )
    # c.create_limit_order_post(intent)  # requires Level 1/2 auth
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType, PartialCreateOrderOptions

from app.config import Settings
from app.models.order import OrderIntent, TimeInForce
from app.models.orderbook import BookLevel, OrderBookSnapshot


class ClobWrapper:
    """CLOB public reads + authenticated orders when credentials present."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        key = settings.private_key.strip() if settings.private_key else None
        funder = settings.funder_address.strip() if settings.funder_address else None
        self._client = ClobClient(
            settings.polymarket_host,
            chain_id=settings.polygon_chain_id,
            key=key,
            funder=funder,
        )
        if settings.api_key and settings.api_secret and settings.api_passphrase:
            self._client.creds = ApiCreds(
                api_key=settings.api_key,
                api_secret=settings.api_secret,
                api_passphrase=settings.api_passphrase,
            )

    def get_order_book(self, token_id: str) -> OrderBookSnapshot:
        raw = self._client.get_order_book(token_id)
        bids: list[BookLevel] = []
        asks: list[BookLevel] = []
        if raw and hasattr(raw, "bids"):
            for b in raw.bids or []:
                bids.append(BookLevel(price=float(b.price), size=float(b.size)))
            for a in raw.asks or []:
                asks.append(BookLevel(price=float(a.price), size=float(a.size)))
        elif isinstance(raw, dict):
            for b in raw.get("bids") or []:
                bids.append(BookLevel(price=float(b.get("price")), size=float(b.get("size", 0))))
            for a in raw.get("asks") or []:
                asks.append(BookLevel(price=float(a.get("price")), size=float(a.get("size", 0))))
        return OrderBookSnapshot(token_id=token_id, bids=bids, asks=asks)

    def get_midpoint(self, token_id: str) -> float | None:
        try:
            m = self._client.get_midpoint(token_id)
            if m is None:
                return None
            return float(m)
        except Exception:
            return None

    def get_spread(self, token_id: str) -> float | None:
        try:
            s = self._client.get_spread(token_id)  # type: ignore[attr-defined]
            return float(s) if s is not None else None
        except Exception:
            return None

    def get_last_trade_price(self, token_id: str) -> float | None:
        try:
            p = self._client.get_last_trade_price(token_id)
            return float(p) if p is not None else None
        except Exception:
            return None

    def create_limit_order_post(self, intent: OrderIntent, *, post_only: bool = False) -> dict[str, Any]:
        """Build and POST limit order (live path only). Maps TIF to SDK OrderType."""
        side = intent.side.value
        exp = 0
        if intent.tif == TimeInForce.GTD and intent.good_til:
            exp = datetime_to_unix(intent.good_til)
        order_args = OrderArgs(
            token_id=intent.token_id,
            price=float(intent.price),
            size=float(intent.size),
            side=side,
            expiration=exp,
        )
        opts: PartialCreateOrderOptions | None = None
        signed = self._client.create_order(order_args, options=opts)
        ot = OrderType.GTC
        if intent.tif == TimeInForce.FOK:
            ot = OrderType.FOK
        elif intent.tif == TimeInForce.FAK:
            ot = OrderType.FAK
        elif intent.tif == TimeInForce.GTD:
            ot = OrderType.GTD
        return self._client.post_order(signed, orderType=ot, post_only=post_only)

    def cancel_all(self) -> Any:
        return self._client.cancel_all()

    def cancel_orders(self, order_ids: list[str]) -> Any:
        return self._client.cancel_orders(order_ids)

    def get_orders(self) -> Any:
        return self._client.get_orders()


def datetime_to_unix(dt: datetime) -> int:
    return int(dt.timestamp())
