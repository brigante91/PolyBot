"""Route order intents from multiple markets with priority and dedup awareness."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import RunMode, Settings
from app.logger import get_logger
from app.models.decision import OperationalAction
from app.models.order import OrderIntent
from app.models.orderbook import OrderBookSnapshot
from app.services.execution_service import ExecutionResult, ExecutionService

log = get_logger("order_router")


@dataclass
class RoutedIntent:
    priority: float
    market_id: str
    intent: OrderIntent
    book: OrderBookSnapshot | None
    strategy_id: str
    confidence: float
    edge_net: float | None = None
    passive_quote: bool = False
    group_key: str = "OTHER"
    trade_allowed: bool = True
    recommended_action: OperationalAction = OperationalAction.NO_TRADE


class OrderRouter:
    """Market-aware ordering: sort by priority score, sequential submit."""

    def __init__(self, settings: Settings, execution: ExecutionService) -> None:
        self._settings = settings
        self._execution = execution

    def route_batch(
        self,
        items: list[RoutedIntent],
        *,
        mode: RunMode,
        bankroll_usd: float,
    ) -> list[tuple[RoutedIntent, ExecutionResult]]:
        items_sorted = sorted(items, key=lambda x: -x.priority)
        out: list[tuple[RoutedIntent, ExecutionResult]] = []
        seen: set[tuple[str, str]] = set()
        for ri in items_sorted:
            if not ri.trade_allowed:
                log.warning("router_skip_not_authorized", market_id=ri.market_id)
                continue
            if ri.recommended_action == OperationalAction.NO_TRADE:
                log.warning("router_skip_no_trade", market_id=ri.market_id)
                continue
            key = (ri.intent.market_id, ri.intent.token_id)
            if key in seen:
                log.info("router_skip_duplicate_market", market_id=ri.market_id)
                continue
            seen.add(key)
            res = self._execution.submit(
                ri.intent,
                mode=mode,
                book=ri.book,
                bankroll_usd=bankroll_usd,
                confidence=ri.confidence,
                edge_net=ri.edge_net,
                use_maker_quote=ri.passive_quote,
                market_id=ri.market_id,
                strategy_id=ri.strategy_id,
            )
            out.append((ri, res))
        return out
