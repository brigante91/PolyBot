"""Per-market decision trace: strategy, edge, action, explainability."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class DecisionTracePanel(Static):
    def render(self) -> str:
        rows = runtime_state.snapshot().get("decisions", [])
        lines = ["[bold]DECISION TRACE[/bold]"]
        for d in rows[-10:]:
            ok = "Y" if d.get("scorer_ok") else "N"
            lines.append(
                f"{str(d.get('market_id',''))[:12]:<12} {ok} {str(d.get('strategy',''))[:14]:<14} "
                f"edge {d.get('edge_net')} conf {d.get('conf')} "
                f"{str(d.get('action',''))[:16]}"
            )
            ex = d.get("explain") or ""
            if ex:
                lines.append(f"  [dim]{ex[:70]}[/dim]")
        if len(lines) == 1:
            lines.append("(run orchestrator to populate)")
        return "\n".join(lines)
