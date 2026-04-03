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
            ta = "Y" if d.get("trade_allowed") else "N"
            xp = "Y" if d.get("execution_passed") else "N"
            lines.append(
                f"{str(d.get('market_id',''))[:12]:<12} {ok} gate={rg} allow={ta} exec={xp} "
                f"{str(d.get('strategy',''))[:12]:<12} 2nd {str(d.get('second',''))[:8]}"
            )
            lines.append(
                f"  eg {d.get('edge_gross')} en {d.get('edge_net')} thr {d.get('threshold_net')} "
                f"conf {d.get('conf')} act {str(d.get('action',''))[:18]}"
            )
            fr = d.get("final_reason") or d.get("reason")
            if fr:
                lines.append(f"  [bold]{str(fr)[:72]}[/bold]")
            rat = d.get("rationale") or d.get("explain") or ""
            if rat:
                lines.append(f"  [dim]{str(rat)[:72]}[/dim]")
        if len(lines) == 1:
            lines.append("(run orchestrator to populate)")
        return "\n".join(lines)
