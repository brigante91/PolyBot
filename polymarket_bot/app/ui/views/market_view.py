"""Market list panel (Textual + Rich markup)."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class MarketPanel(Static):
    """Markets table: id, score, strategy, edge, fair/mkt."""

    def render(self) -> str:
        snap = runtime_state.snapshot()
        lines = ["[bold]MARKETS[/bold]"]
        for m in snap.get("markets", [])[:20]:
            lines.append(
                f"{m.get('id','')[:12]:<12} sc {m.get('score',0):.2f} "
                f"{str(m.get('strategy',''))[:14]:<14} edge {m.get('edge',''):>6} "
                f"fv {m.get('fair','')} mkt {m.get('mkt','')}"
            )
        if len(lines) == 1:
            lines.append("(no data — run orchestrator in another terminal)")
        return "\n".join(lines)
