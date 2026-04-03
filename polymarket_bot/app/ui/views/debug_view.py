"""Recent debug / decision lines."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class DebugPanel(Static):
    def render(self) -> str:
        snap = runtime_state.snapshot()
        lines = list(snap.get("debug", [])[-14:])
        hints = snap.get("no_trade_hints", [])
        out = ["[bold]DEBUG[/bold]"]
        if hints:
            out.append("[dim]no-trade (latest):[/dim]")
            for h in hints[-5:]:
                out.append(f"  {h}")
        out.extend(lines if lines else ["—"])
        return "\n".join(out)
