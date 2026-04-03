"""System health panel."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class SystemPanel(Static):
    def render(self) -> str:
        s = runtime_state.snapshot().get("system", {})
        ws = s.get("ws", "N/A")
        lat = s.get("latency_ms", "—")
        health = s.get("health", "UNKNOWN")
        risk = runtime_state.snapshot().get("risk_level", 1.0)
        return (
            f"[bold]SYSTEM[/bold]\n"
            f"WS: {ws} | Latency: {lat}ms | Health: {health}\n"
            f"Paused: {runtime_state.snapshot().get('paused', False)} | Risk x{risk}\n"
        )
