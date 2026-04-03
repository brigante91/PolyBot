"""End-to-end paper simulation (no network)."""

from __future__ import annotations

from app.config import Settings
from app.models.order import OrderIntent, OrderSide, TimeInForce
from app.models.orderbook import BookLevel, OrderBookSnapshot
from app.paper.paper_broker import PaperBroker
from app.utils.time import utc_now


def test_paper_broker_fill() -> None:
    settings = Settings(
        MODE="paper",
        ENABLE_LIVE_TRADING=False,
        MAX_ORDER_SIZE_USD=25,
        MAX_TOTAL_EXPOSURE_USD=300,
        DAILY_LOSS_LIMIT_USD=50,
        MAX_OPEN_ORDERS=10,
    )
    pb = PaperBroker(settings)
    book = OrderBookSnapshot(
        token_id="t",
        bids=[BookLevel(price=0.48, size=1000)],
        asks=[BookLevel(price=0.52, size=1000)],
        fetched_at=utc_now(),
    )
    intent = OrderIntent(
        market_id="m",
        token_id="t",
        side=OrderSide.BUY,
        price=0.5,
        size=100,
        tif=TimeInForce.GTC,
    )
    out = pb.simulate_fill(intent, book)
    assert "fill_price" in out
    assert out["fee_usd"] >= 0
