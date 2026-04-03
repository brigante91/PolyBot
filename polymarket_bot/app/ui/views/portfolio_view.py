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
        per = p.get("per_market_usd") or {}
        lines = [
            "[bold]PORTFOLIO[/bold]",
            f"Exposure: {exp}% | Capital used: {cap}%",
            f"Daily PnL: {dpnl}% | Open positions: {op}",
        ]
        if isinstance(per, dict) and per:
            lines.append("Per market (USD):")
            for k, v in list(per.items())[:8]:
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)
