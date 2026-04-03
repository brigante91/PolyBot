"""
Single writer path from operational state (RealtimeStateEngine + orchestrator data) → runtime_state (TUI).

Orchestrator should call `project_cycle` once per logical update instead of scattering runtime_state.update.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.state.runtime_state import runtime_state

if TYPE_CHECKING:
    from app.execution.reconciliation import ReconciliationService
    from app.realtime.state_engine import RealtimeStateEngine


def project_cycle(
    *,
    markets: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    portfolio: dict[str, Any],
    system: dict[str, Any],
    metrics: dict[str, Any],
    risk_limits: dict[str, Any],
    rt_engine: RealtimeStateEngine | None,
    recon: ReconciliationService,
    positions: list[dict[str, Any]] | None = None,
    trades: list[dict[str, Any]] | None = None,
    runtime_mode: str | None = None,
    ui_mode: str | None = None,
) -> None:
    """Merge realtime engine snapshot with orchestrator fields; one atomic runtime_state.update."""
    rt_snap: dict[str, Any] = rt_engine.snapshot() if rt_engine else {}
    trades_out = trades if trades is not None else list(rt_snap.get("recent_fills", []))[-40:]
    feeds = rt_snap.get("feeds") or {}
    system_merged = {
        **system,
        "market_ws_ok": feeds.get("market_ok"),
        "user_ws_ok": feeds.get("user_ok"),
        "market_reconnects": feeds.get("market_reconnect_count", 0),
        "user_reconnects": feeds.get("user_reconnect_count", 0),
        "market_last_error": feeds.get("market_last_error"),
        "user_last_error": feeds.get("user_last_error"),
        "stale_asset_count": sum(1 for b in rt_snap.get("books", []) if b.get("stale")),
    }
    risk_block = {
        **risk_limits,
        "reconciliation": recon.snapshot(),
        "realtime_engine": rt_snap,
    }
    runtime_state.update(
        markets=markets,
        decisions=decisions,
        orders=orders,
        portfolio=portfolio,
        system=system_merged,
        metrics=metrics,
        risk=risk_block,
        positions=positions or [],
        trades=trades_out,
        runtime_mode=runtime_mode,
        ui_mode=ui_mode,
    )
