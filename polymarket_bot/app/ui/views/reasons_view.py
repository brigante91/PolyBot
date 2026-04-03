"""No-trade and risk-reject reasons (projection)."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class ReasonsPanel(Static):
    def render(self) -> str:
        snap = runtime_state.snapshot()
        nt = snap.get("no_trade_hints", [])
        rr = snap.get("risk_reject_hints", [])
        lines = ["[bold]NO TRADE / RISK[/bold]"]
        if rr:
            lines.append("[red]Risk rejects:[/red]")
            for x in rr[-8:]:
                lines.append(f"  {x[:78]}")
        if nt:
            lines.append("[dim]No-trade:[/dim]")
            for x in nt[-8:]:
                lines.append(f"  {x[:78]}")
        if not rr and not nt:
            lines.append("(none this session)")
        return "\n".join(lines)
