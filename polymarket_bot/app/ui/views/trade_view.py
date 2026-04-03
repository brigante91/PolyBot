"""Positions / fills from runtime projection."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class TradePanel(Static):
    def render(self) -> str:
        snap = runtime_state.snapshot()
        pos = snap.get("positions", [])
        fills = snap.get("trades", [])
        lines = ["[bold]POSITIONS / FILLS[/bold]"]
        for p in pos[:12]:
            if isinstance(p, dict):
                lines.append(
                    f"{str(p.get('market_id',''))[:12]:<12} {p.get('side','—')} "
                    f"${p.get('size_usd','')} avg {p.get('avg_entry','—')} "
                    f"u {p.get('unreal_pnl','—')} r {p.get('real_pnl','—')}"
                )
        if not pos:
            lines.append("(no position rows — exposure may be empty)")
        lines.append("[bold]Recent fills[/bold]")
        for t in fills[-6:]:
            if isinstance(t, dict):
                lines.append(str(t.get("order_id", t.get("market_id", "")))[:40])
        if len(lines) <= 3 and not fills:
            lines.append("(no fills yet)")
        return "\n".join(lines)
