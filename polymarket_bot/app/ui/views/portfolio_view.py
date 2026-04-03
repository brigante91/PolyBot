"""Portfolio summary panel."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class PortfolioPanel(Static):
    def render(self) -> str:
        p = runtime_state.snapshot().get("portfolio", {})
        exp = p.get("exposure_pct", "—")
        dpnl = p.get("daily_pnl_pct", "—")
        op = p.get("open_positions", "—")
        cap = p.get("capital_used_pct", "—")
        return (
            f"[bold]PORTFOLIO[/bold]\n"
            f"Exposure: {exp}%\n"
            f"Capital used: {cap}\n"
            f"Daily PnL: {dpnl}%\n"
            f"Open positions: {op}\n"
        )
