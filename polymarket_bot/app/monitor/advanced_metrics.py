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
    markets_strategy_selected: int = 0
    markets_trade_allowed: int = 0
    markets_no_trade_gate: int = 0
    no_trade_reasons: dict[str, int] = field(default_factory=dict)
    edge_avg_allowed: float = 0.0
    edge_avg_rejected: float = 0.0
    orders_filled: int = 0
    orders_cancelled: int = 0
    orders_sent: int = 0
    _edge_in_sum: float = 0.0
    _edge_in_n: int = 0
    _edge_realized_sum: float = 0.0
    _edge_realized_n: int = 0
    _maker_fills: int = 0
    _taker_fills: int = 0
    _edge_allowed_sum: float = 0.0
    _edge_allowed_n: int = 0
    _edge_rejected_sum: float = 0.0
    _edge_rejected_n: int = 0

    def record_trade_gate_outcome(
        self,
        *,
        strategy_selected: bool,
        trade_allowed: bool,
        reason: str,
        edge_net: float | None,
    ) -> None:
        if strategy_selected:
            self.markets_strategy_selected += 1
        if trade_allowed:
            self.markets_trade_allowed += 1
            if edge_net is not None:
                self._edge_allowed_sum += float(edge_net)
                self._edge_allowed_n += 1
                self.edge_avg_allowed = self._edge_allowed_sum / max(self._edge_allowed_n, 1)
        else:
            self.markets_no_trade_gate += 1
            self.no_trade_reasons[reason] = self.no_trade_reasons.get(reason, 0) + 1
            if edge_net is not None:
                self._edge_rejected_sum += float(edge_net)
                self._edge_rejected_n += 1
                self.edge_avg_rejected = self._edge_rejected_sum / max(self._edge_rejected_n, 1)

    def record_edge_at_entry(self, edge_net: float) -> None:
        self._edge_in_sum += float(edge_net)
        self._edge_in_n += 1
        self.edge_in_avg = self._edge_in_sum / max(self._edge_in_n, 1)

    def record_edge_realized(self, edge: float) -> None:
        self._edge_realized_sum += float(edge)
        self._edge_realized_n += 1
        self.edge_realized_avg = self._edge_realized_sum / max(self._edge_realized_n, 1)

    def record_order_submitted(self) -> None:
        self.orders_sent += 1
        self._recompute_ratios()

    def record_fill(self, *, maker: bool = True) -> None:
        self.orders_filled += 1
        if maker:
            self._maker_fills += 1
        else:
            self._taker_fills += 1
        self._recompute_ratios()

    def record_cancel(self) -> None:
        self.orders_cancelled += 1
        self._recompute_ratios()

    def update_no_trade_ratio(self, no_trade: int, decisions: int) -> None:
        self.no_trade_ratio = float(no_trade) / max(decisions, 1)

    def add_pnl_strategy(self, strategy_id: str, pnl_usd: float) -> None:
        self.pnl_by_strategy[strategy_id] = self.pnl_by_strategy.get(strategy_id, 0.0) + pnl_usd

    def add_pnl_market(self, market_id: str, pnl_usd: float) -> None:
        self.pnl_by_market[market_id] = self.pnl_by_market.get(market_id, 0.0) + pnl_usd

    def _recompute_ratios(self) -> None:
        self.fill_rate = self.orders_filled / max(self.orders_sent, 1)
        denom = self.orders_filled + self.orders_cancelled
        self.cancel_ratio = self.orders_cancelled / max(denom, 1)
        if self._taker_fills <= 0:
            self.maker_taker_ratio = float(self._maker_fills) if self._maker_fills else 0.0
        else:
            self.maker_taker_ratio = self._maker_fills / max(self._taker_fills, 1e-9)

    def to_dict(self) -> dict[str, float | dict[str, float]]:
        return {
            "edge_in_avg": round(self.edge_in_avg, 5),
            "edge_realized_avg": round(self.edge_realized_avg, 5),
            "fill_rate": round(self.fill_rate, 4),
            "cancel_ratio": round(self.cancel_ratio, 4),
            "maker_taker_ratio": round(self.maker_taker_ratio, 4),
            "no_trade_ratio": round(self.no_trade_ratio, 4),
            "markets_strategy_selected": float(self.markets_strategy_selected),
            "markets_trade_allowed": float(self.markets_trade_allowed),
            "markets_no_trade_gate": float(self.markets_no_trade_gate),
            "no_trade_reasons": dict(self.no_trade_reasons),
            "edge_avg_allowed": round(self.edge_avg_allowed, 6),
            "edge_avg_rejected": round(self.edge_avg_rejected, 6),
            "orders_sent": float(self.orders_sent),
            "orders_filled": float(self.orders_filled),
            "orders_cancelled": float(self.orders_cancelled),
            "pnl_by_strategy": dict(self.pnl_by_strategy),
            "pnl_by_market": dict(self.pnl_by_market),
        }
