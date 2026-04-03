"""System health panel."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class SystemPanel(Static):
    def render(self) -> str:
        s = runtime_state.snapshot().get("system", {})
        snap = runtime_state.snapshot()
        ws = s.get("ws", "N/A")
        lat = s.get("latency_ms", "—")
        health = s.get("health", "UNKNOWN")
        risk = snap.get("risk_level", 1.0)
        ks = s.get("kill_switch", False)
        sk = snap.get("soft_kill", False)
        gate = s.get("execution_gate", "—")
        m_ok = s.get("market_ws_ok")
        u_ok = s.get("user_ws_ok")
        m_rc = s.get("market_reconnects", "—")
        u_rc = s.get("user_reconnects", "—")
        stale_n = s.get("stale_asset_count", "—")
        doc = snap.get("doctor_last", {})
        doc_s = doc.get("status", "—") if doc else "—"
        rm = snap.get("runtime_mode", "—")
        ui = snap.get("ui_mode", "—")
        lines = [
            "[bold]SYSTEM HEALTH[/bold]",
            f"mode={rm} ui={ui} | WS(rest)={ws} | Lat={lat}ms | {health}",
            f"mktWS ok={m_ok} rc={m_rc} | usrWS ok={u_ok} rc={u_rc} | stale_assets={stale_n}",
            f"Gate: {gate} | KillSW: {ks} | SoftKill: {sk} | Pause: {snap.get('paused')}",
            f"Risk x{risk} | last doctor: {doc_s}",
        ]
        return "\n".join(lines)
