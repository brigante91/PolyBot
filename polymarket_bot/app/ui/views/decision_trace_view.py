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
            rg = str(d.get("risk_gate", "—"))[:12]
            lines.append(
                f"{str(d.get('market_id',''))[:12]:<12} {ok} gate={rg} "
                f"{str(d.get('strategy',''))[:12]:<12} 2nd {str(d.get('second',''))[:8]}"
            )
            lines.append(
                f"  edge {d.get('edge_net')} conf {d.get('conf')} act {str(d.get('action',''))[:20]}"
            )
            rat = d.get("rationale") or d.get("explain") or ""
            if rat:
                lines.append(f"  [dim]{str(rat)[:72]}[/dim]")
        if len(lines) == 1:
            lines.append("(run orchestrator to populate)")
        return "\n".join(lines)
