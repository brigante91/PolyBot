"""Market list panel (Textual + Rich markup)."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class MarketPanel(Static):
    """Markets table: id, score, strategy, edge, fair/mkt, stale/blocked."""

    def render(self) -> str:
        snap = runtime_state.snapshot()
        lines = ["[bold]MARKET RADAR[/bold]"]
        for m in snap.get("markets", [])[:18]:
            trad = "Y" if m.get("tradable") else "N"
            st = "STALE" if m.get("stale") else "live"
            blk = "BLOCK" if m.get("blocked") else "ok"
            lines.append(
                f"{str(m.get('id',''))[:10]:<10} {trad} {st} {blk} sc{m.get('score',0):.2f} "
                f"{str(m.get('strategy',''))[:12]:<12} conf {m.get('confidence',''):>4} "
                f"edge {m.get('edge',''):>6} fv {m.get('fair','')} mkt {m.get('mkt','')}"
            )
            ex = str(m.get("explain", ""))[:50]
            if ex:
                lines.append(f"  [dim]{ex}[/dim]")
        if len(lines) == 1:
            lines.append("(no data — start orchestrator from launcher)")
        return "\n".join(lines)
