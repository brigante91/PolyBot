"""Recent orders / full lifecycle (intent → … → filled / cancel / reject)."""

from __future__ import annotations

from textual.widgets import Static

from app.models.order_lifecycle import OrderLifecycle
from app.state.runtime_state import runtime_state

_LIFECYCLE_ORDER = frozenset(
    {
        OrderLifecycle.INTENT.value,
        "routed",
        OrderLifecycle.SENT.value,
        OrderLifecycle.ACK.value,
        OrderLifecycle.PARTIAL_FILL.value,
        OrderLifecycle.FILLED.value,
        OrderLifecycle.CANCELLED.value,
        OrderLifecycle.REJECTED.value,
        "dry_run",
        "test",
        "paper",
        "sent",
        "rejected",
    }
)


class OrderBlotterPanel(Static):
    def render(self) -> str:
        rows = runtime_state.snapshot().get("orders", [])
        lines = [
            "[bold]ORDER BLOTTER[/bold]",
            "[dim]lifecycle: intent→sent→ack→partial→filled | cancel | reject | dry/test/paper[/dim]",
        ]
        for o in rows[-14:]:
            lc = str(o.get("lifecycle", "?"))
            stage = "★" if lc in _LIFECYCLE_ORDER else "·"
            lines.append(
                f"{stage} {lc:<12} {str(o.get('market_id',''))[:10]} "
                f"{o.get('side','')} @{o.get('price')} sz {o.get('size')} "
                f"{str(o.get('strategy',''))[:10]} "
                f"{'OK' if o.get('ok') else o.get('reason','')}"
            )
        if len(lines) == 2:
            lines.append("(no orders — run orchestrator)")
        return "\n".join(lines)
