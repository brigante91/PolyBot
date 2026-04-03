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
        snap = runtime_state.snapshot()
        ks = s.get("kill_switch", False)
        sk = snap.get("soft_kill", False)
        gate = s.get("execution_gate", "—")
        return (
            f"[bold]SYSTEM[/bold]\n"
            f"WS: {ws} | Lat: {lat}ms | Health: {health}\n"
            f"Gate: {gate} | KillSW: {ks} | SoftKill: {sk}\n"
            f"Pause: {snap.get('paused', False)} | Risk x{risk}\n"
        )
