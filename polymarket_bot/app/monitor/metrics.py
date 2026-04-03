"""Counters for observability (structured logs consume these)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OrchestratorMetrics:
    scanned: int = 0
    filtered_out: int = 0
    live_analyzed: int = 0
    ranked: int = 0
    no_trade: int = 0
    routed: int = 0
    rejected_risk: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "scanned": self.scanned,
            "filtered_out": self.filtered_out,
            "live_analyzed": self.live_analyzed,
            "ranked": self.ranked,
            "no_trade": self.no_trade,
            "routed": self.routed,
            "rejected_risk": self.rejected_risk,
        }


@dataclass
class AlertSink:
    """Placeholder for external alerts."""

    messages: list[str] = field(default_factory=list)

    def emit(self, level: str, msg: str) -> None:
        self.messages.append(f"{level}:{msg}")
