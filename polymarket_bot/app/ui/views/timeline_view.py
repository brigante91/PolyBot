"""Replay / audit event timeline (last N events)."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class TimelinePanel(Static):
    def render(self) -> str:
        snap = runtime_state.snapshot()
        ev = snap.get("timeline", [])
        lines = ["[bold]TIMELINE[/bold]"]
        if snap.get("replay_mode"):
            lines.append("[yellow]REPLAY MODE[/yellow]")
        for e in ev[-12:]:
            if isinstance(e, dict):
                t = e.get("t", e.get("type", ""))
                d = str(e.get("detail", e.get("msg", "")))[:60]
                lines.append(f"{t} {d}")
            else:
                lines.append(str(e)[:70])
        if len(lines) == 1:
            lines.append("(no events)")
        return "\n".join(lines)
