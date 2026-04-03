"""Configured risk limits and reconciliation / realtime hints."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class RiskPanel(Static):
    def render(self) -> str:
        r = runtime_state.snapshot().get("risk", {})
        if not r:
            return "[bold]RISK[/bold]\n(no snapshot yet)"
        recon = r.get("reconciliation") or {}
        rt = r.get("realtime_engine") or {}
        lines = [
            "[bold]RISK[/bold]",
            f"max_order ${r.get('max_order_usd','?')} | max_total ${r.get('max_total_exposure_usd','?')}",
            f"group ${r.get('max_group_exposure_usd','?')} | daily_loss ${r.get('daily_loss_limit_usd','?')}",
            f"max_open_orders {r.get('max_open_orders','?')}",
            f"recon_tracked={recon.get('orders_tracked','?')} | ws_mkt={rt.get('ws_market_ok')} usr={rt.get('ws_user_ok')}",
            f"books={rt.get('assets_tracked','?')} reconnects={rt.get('reconnect_count','?')}",
        ]
        return "\n".join(lines)
