"""Advanced metrics: edge, fill quality, maker/taker, ratios."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AdvancedMetrics:
    edge_in_avg: float = 0.0
    edge_realized_avg: float = 0.0
    fill_rate: float = 0.0
    cancel_ratio: float = 0.0
    maker_taker_ratio: float = 0.0
    pnl_by_strategy: dict[str, float] = field(default_factory=dict)
    pnl_by_market: dict[str, float] = field(default_factory=dict)
    no_trade_ratio: float = 0.0
    orders_filled: int = 0
    orders_cancelled: int = 0
    orders_sent: int = 0

    def record_fill(self, maker: bool) -> None:
        self.orders_filled += 1
        # incremental EMA could be added; keep simple counters for V3
        _ = maker
