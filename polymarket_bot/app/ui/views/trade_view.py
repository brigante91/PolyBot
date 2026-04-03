"""Active trades / positions panel."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class TradePanel(Static):
    def render(self) -> str:
        snap = runtime_state.snapshot()
        lines = ["[bold]ACTIVE / TRADES[/bold]"]
        for t in snap.get("trades", [])[:15]:
            if isinstance(t, dict):
                mid = str(t.get("market_id", t.get("id", "")))[:10]
                side = t.get("side", "")
                sz = t.get("size", "")
                pnl = t.get("pnl_pct", t.get("pnl", ""))
                lines.append(f"{mid:<10} {side} sz {sz} pnl {pnl}")
            else:
                lines.append(str(t))
        if len(lines) == 1:
            lines.append("(none — positions feed from orchestrator)")
        return "\n".join(lines)
