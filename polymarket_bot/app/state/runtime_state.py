"""Thread-safe snapshot for TUI / observability (updated by orchestrator & WS)."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeState:
    markets: list[dict[str, Any]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    portfolio: dict[str, Any] = field(default_factory=dict)
    system: dict[str, Any] = field(default_factory=dict)
    debug_lines: deque[str] = field(default_factory=lambda: deque(maxlen=200))
    updated_at: float = field(default_factory=time.time)
    paused: bool = False
    _lock: threading.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_lock", threading.Lock())

    def update(
        self,
        *,
        markets: list[dict[str, Any]] | None = None,
        trades: list[dict[str, Any]] | None = None,
        portfolio: dict[str, Any] | None = None,
        system: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            if markets is not None:
                self.markets = markets
            if trades is not None:
                self.trades = trades
            if portfolio is not None:
                self.portfolio = portfolio
            if system is not None:
                self.system = system
            self.updated_at = time.time()

    def push_debug(self, line: str) -> None:
        with self._lock:
            self.debug_lines.append(line)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "markets": list(self.markets),
                "trades": list(self.trades),
                "portfolio": dict(self.portfolio),
                "system": dict(self.system),
                "debug": list(self.debug_lines)[-50:],
                "updated_at": self.updated_at,
                "paused": self.paused,
            }


runtime_state = RuntimeState()
