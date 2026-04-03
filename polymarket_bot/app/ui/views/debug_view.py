"""Recent debug lines (no-trade / risk moved to Reasons panel)."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class DebugPanel(Static):
    def render(self) -> str:
        snap = runtime_state.snapshot()
        lines = list(snap.get("debug", [])[-16:])
        out = ["[bold]DEBUG[/bold]"]
        out.extend(lines if lines else ["—"])
        return "\n".join(out)
