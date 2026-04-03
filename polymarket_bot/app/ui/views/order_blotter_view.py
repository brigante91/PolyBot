"""Recent orders / execution lifecycle (orchestrator-fed)."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class OrderBlotterPanel(Static):
    def render(self) -> str:
        rows = runtime_state.snapshot().get("orders", [])
        lines = ["[bold]ORDER BLOTTER[/bold]"]
        for o in rows[-12:]:
            lines.append(
                f"{o.get('lifecycle','?'):<10} {str(o.get('market_id',''))[:10]} "
                f"{o.get('side','')} @{o.get('price')} sz {o.get('size')} "
                f"po={o.get('post_only')} {o.get('strategy','')[:10]} "
                f"{'OK' if o.get('ok') else o.get('reason','')}"
            )
        if len(lines) == 1:
            lines.append("(no orders this cycle)")
        return "\n".join(lines)
