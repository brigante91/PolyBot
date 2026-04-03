"""Per-market risk policies (thin layer over RiskEngine)."""

from __future__ import annotations

from app.config import RunMode
from app.models.order import OrderIntent
from app.models.orderbook import OrderBookSnapshot
from app.models.risk import RiskCheckResult
from app.risk.risk_engine import RiskEngine


def check_market_intent(
    risk: RiskEngine,
    intent: OrderIntent,
    *,
    mode: RunMode,
    book: OrderBookSnapshot | None,
    notional_usd: float,
    is_adding_to_loser: bool,
) -> RiskCheckResult:
    return risk.check_pre_trade(
        intent,
        mode=mode,
        book=book,
        notional_usd=notional_usd,
        is_adding_to_loser=is_adding_to_loser,
    )
