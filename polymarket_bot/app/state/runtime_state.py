"""Thread-safe snapshot for TUI / observability (updated by orchestrator & WS)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeState:
    markets: list[dict[str, Any]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    """Recent order / execution rows for TUI blotter."""
    orders: list[dict[str, Any]] = field(default_factory=list)
    """Per-market decision trace (strategy, edge, action, explain)."""
    decisions: list[dict[str, Any]] = field(default_factory=list)
    portfolio: dict[str, Any] = field(default_factory=dict)
    system: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    debug_lines: list[str] = field(default_factory=list)
    no_trade_hints: list[str] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)
    paused: bool = False
    """TUI 'k' — block new order routing until cleared (soft halt)."""
    soft_kill: bool = False
    risk_level: float = 1.0
    _lock: threading.Lock = field(init=False, repr=False)
    _max_debug: int = 200
    _max_hints: int = 80

    def __post_init__(self) -> None:
        object.__setattr__(self, "_lock", threading.Lock())

    def update(
        self,
        *,
        markets: list[dict[str, Any]] | None = None,
        trades: list[dict[str, Any]] | None = None,
        orders: list[dict[str, Any]] | None = None,
        decisions: list[dict[str, Any]] | None = None,
        portfolio: dict[str, Any] | None = None,
        system: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            if markets is not None:
                self.markets = markets
            if trades is not None:
                self.trades = trades
            if orders is not None:
                self.orders = orders
            if decisions is not None:
                self.decisions = decisions
            if portfolio is not None:
                self.portfolio = portfolio
            if system is not None:
                self.system = system
            if metrics is not None:
                self.metrics = metrics
            self.updated_at = time.time()

    def push_debug(self, line: str) -> None:
        with self._lock:
            self.debug_lines.append(line)
            self.debug_lines[:] = self.debug_lines[-self._max_debug :]

    def push_no_trade(self, market_id: str, reason: str) -> None:
        with self._lock:
            self.no_trade_hints.append(f"{market_id[:10]}… {reason}")
            self.no_trade_hints[:] = self.no_trade_hints[-self._max_hints :]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "markets": list(self.markets),
                "trades": list(self.trades),
                "orders": list(self.orders),
                "decisions": list(self.decisions),
                "portfolio": dict(self.portfolio),
                "system": dict(self.system),
                "metrics": dict(self.metrics),
                "debug": list(self.debug_lines)[-50:],
                "no_trade_hints": list(self.no_trade_hints)[-20:],
                "updated_at": self.updated_at,
                "paused": self.paused,
                "soft_kill": self.soft_kill,
                "risk_level": self.risk_level,
            }


runtime_state = RuntimeState()
