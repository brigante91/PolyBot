"""Advanced metrics snapshot (edge, fill, ratios)."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class MetricsPanel(Static):
    def render(self) -> str:
        m = runtime_state.snapshot().get("metrics", {})
        if not m:
            return "[bold]METRICS[/bold]\n—"
        lines = [
            "[bold]METRICS[/bold]",
            f"edge_in_avg {m.get('edge_in_avg')}  edge_out {m.get('edge_realized_avg')}",
            f"fill_rate {m.get('fill_rate')}  cancel_ratio {m.get('cancel_ratio')}",
            f"maker/taker {m.get('maker_taker_ratio')}  no_trade {m.get('no_trade_ratio')}",
            f"sent {int(m.get('orders_sent',0))}  filled {int(m.get('orders_filled',0))}  cxl {int(m.get('orders_cancelled',0))}",
        ]
        return "\n".join(lines)
