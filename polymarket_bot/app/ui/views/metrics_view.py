"""Advanced metrics snapshot (edge, fill, ratios)."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class MetricsPanel(Static):
    def render(self) -> str:
        m = runtime_state.snapshot().get("metrics", {})
        if not m:
            return "[bold]METRICS[/bold]\n—"
        ps = m.get("pnl_by_strategy") or {}
        pm = m.get("pnl_by_market") or {}
        lines = [
            "[bold]METRICS[/bold]",
            f"edge_in_avg {m.get('edge_in_avg')}  edge_real {m.get('edge_realized_avg')}",
            f"fill_rate {m.get('fill_rate')}  cancel_ratio {m.get('cancel_ratio')}",
            f"maker/taker {m.get('maker_taker_ratio')}  no_trade {m.get('no_trade_ratio')}",
            f"sent {int(m.get('orders_sent',0))}  filled {int(m.get('orders_filled',0))}  cxl {int(m.get('orders_cancelled',0))}",
        ]
        if isinstance(ps, dict) and ps:
            parts = []
            for k, v in list(ps.items())[:5]:
                try:
                    parts.append(f"{k}:{float(v):.2f}")
                except (TypeError, ValueError):
                    parts.append(f"{k}:{v}")
            lines.append("PnL by strategy: " + ", ".join(parts))
        if isinstance(pm, dict) and pm:
            parts_m = []
            for k, v in list(pm.items())[:5]:
                try:
                    parts_m.append(f"{str(k)[:8]}:{float(v):.2f}")
                except (TypeError, ValueError):
                    parts_m.append(f"{str(k)[:8]}:{v}")
            lines.append("PnL by mkt: " + ", ".join(parts_m))
        return "\n".join(lines)
