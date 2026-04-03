"""WebSocket / feed health (from RealtimeStateEngine projection in risk + system)."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class FeedHealthPanel(Static):
    def render(self) -> str:
        snap = runtime_state.snapshot()
        r = snap.get("risk", {})
        rt = r.get("realtime_engine") or {}
        feeds = rt.get("feeds") or {}
        s = snap.get("system", {})
        lines = [
            "[bold]FEED HEALTH[/bold]",
            f"market WS: ok={feeds.get('market_ok', s.get('market_ws_ok'))} "
            f"rc={feeds.get('market_reconnect_count', s.get('market_reconnects', '—'))}",
            f"user WS: ok={feeds.get('user_ok', s.get('user_ws_ok'))} "
            f"rc={feeds.get('user_reconnect_count', s.get('user_reconnects', '—'))}",
        ]
        if feeds.get("market_last_error") or s.get("market_last_error"):
            lines.append(f"[red]mkt err: {feeds.get('market_last_error') or s.get('market_last_error')}[/red]")
        if feeds.get("user_last_error") or s.get("user_last_error"):
            lines.append(f"[red]usr err: {feeds.get('user_last_error') or s.get('user_last_error')}[/red]")
        books = rt.get("books") or []
        stale_n = sum(1 for b in books if b.get("stale"))
        lines.append(f"books tracked: {len(books)} | stale rows: {stale_n}")
        if s.get("user_ws_degraded") or s.get("execution_gate") == "USER_WS_DEGRADED":
            lines.append("[yellow]SAFE: user feed degraded — new opens blocked (live)[/yellow]")
        return "\n".join(lines)
