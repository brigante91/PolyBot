"""CLI — orchestration only; business logic lives in services."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
import typer
from rich import print as rprint
from rich.table import Table

from app.backtest.engine import BacktestEngine
from app.backtest.metrics import write_csv
from app.clients.clob_client import ClobWrapper
from app.clients.gamma_client import GammaClient
from app.config import RunMode, load_settings
from app.logger import configure_logging, get_logger
from app.services.persistence_service import PersistenceService
from app.runtime import run_multi_market
from app.services.trading_service import TradingService
from app.ui.tui_launcher import main as tui_main

app = typer.Typer(add_completion=False, no_args_is_help=True)
log = get_logger("cli")


@app.command("check-env")
def check_env_cmd() -> None:
    """Validate local install, paths, and optional deps (no network)."""
    from app.cli_health import run_check_env

    raise typer.Exit(run_check_env())


@app.command("doctor")
def doctor_cmd() -> None:
    """Smoke test: package import, data dir, Gamma/CLOB reachability (public HTTP)."""
    from app.cli_health import run_doctor

    raise typer.Exit(run_doctor())


@app.command("replay")
def replay_cmd(
    path: str = typer.Argument(..., help="Session JSONL (data/sessions/session_*.jsonl)"),
    speed: float = typer.Option(1.0, "--speed", help="Replay speed multiplier"),
    max_lines: Optional[int] = typer.Option(None, "--max-lines"),
) -> None:
    """Replay a recorded JSONL session into the TUI snapshot buffer (offline review)."""
    from pathlib import Path

    from app.data.replay_engine import replay_file

    p = Path(path)
    if not p.is_file():
        rprint(f"[red]File not found: {p}[/red]")
        raise typer.Exit(1)
    n = replay_file(p, speed=speed, max_lines=max_lines)
    rprint(f"[green]Replayed {n} records from {p}[/green]")
    raise typer.Exit(0)


@app.command("backfill-history")
def backfill_history_cmd() -> None:
    """Backfill historical snapshots for closed markets — stub."""
    rprint("[yellow]backfill-history: stub — implement with app.data.recorder when ready[/yellow]")
    raise typer.Exit(0)


@app.command("flatten-all")
def flatten_all_cmd() -> None:
    """Cancel all open CLOB orders (live). Does not net out positions — close those separately."""
    settings = load_settings()
    configure_logging(settings.log_level)
    if not settings.enable_live_trading:
        rprint("[yellow]flatten-all: set ENABLE_LIVE_TRADING=true in .env[/yellow]")
        raise typer.Exit(1)
    clob = ClobWrapper(settings)
    out = clob.cancel_all()
    rprint(out)
    raise typer.Exit(0)


@app.command("tui")
def tui_cmd() -> None:
    """Terminal UI with launcher (same as polybot-tui)."""
    tui_main()


@app.command("discover-markets")
def discover_markets(limit: int = typer.Option(20, help="Max markets to fetch")) -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    g = GammaClient(settings)
    try:
        markets = g.fetch_markets_page(active=True, closed=False, limit=limit)
        t = Table(title="Gamma markets (sample)")
        t.add_column("id")
        t.add_column("question")
        t.add_column("liquidity")
        for m in markets[:limit]:
            t.add_row(m.id, (m.question or "")[:60], str(m.liquidity_num or ""))
        rprint(t)
    finally:
        g.close()


@app.command("run-multi")
def run_multi_cmd(
    mode: str = typer.Option("paper", "--mode", help="paper|dry_run|live|test"),
    max_cycles: Optional[int] = typer.Option(None, "--max-cycles"),
) -> None:
    """Multi-market adaptive orchestrator (scan → filter → score → select → route)."""
    settings = load_settings()
    m = RunMode(mode) if mode in ("paper", "dry_run", "live", "test") else RunMode.PAPER
    mc = max_cycles if max_cycles is not None else (1 if m == RunMode.TEST else None)
    run_multi_market(settings, mode=m, max_cycles=mc)


@app.command("run")
def run_cmd(
    mode: str = typer.Option("paper", "--mode", help="paper|dry_run|live|test"),
    strategy: Optional[str] = typer.Option(None, "--strategy"),
    max_iter: Optional[int] = typer.Option(None, "--max-iter"),
) -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    m = RunMode(mode) if mode in ("paper", "dry_run", "live", "test") else RunMode.PAPER
    svc = TradingService(settings)
    try:
        svc.run_loop(mode=m, strategy_name=strategy, max_iterations=max_iter)
    finally:
        svc.shutdown()


@app.command("backtest")
def backtest_cmd(
    strategy: str = typer.Option("mean_reversion_micro", "--strategy"),
    from_date: str = typer.Option("2025-01-01", "--from"),
    to_date: str = typer.Option("2025-03-01", "--to"),
    out: str = typer.Option("outputs/backtest_metrics.csv", "--out"),
) -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    # Synthetic bars when no file — demonstrates pipeline; research should load real history.
    dates = pd.date_range(from_date, to_date, freq="D")
    df = pd.DataFrame(
        {
            "close": [0.45 + 0.01 * (i % 7) for i in range(len(dates))],
            "spread_bps": [80 + i % 40 for i in range(len(dates))],
            "depth_usd": [5000] * len(dates),
            "vol_score": [0.1] * len(dates),
            "mom": [0.2 + 0.05 * (i % 3) for i in range(len(dates))],
            "vol_conf": [0.8] * len(dates),
        },
        index=dates,
    )
    eng = BacktestEngine(settings)
    metrics = eng.run_from_df(df, strategy_name=strategy)
    outp = Path(out)
    if not outp.is_absolute():
        outp = Path.cwd() / outp
    write_csv(outp, metrics)
    rprint(metrics.to_row())


@app.command("status")
def status_cmd() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    p = PersistenceService(settings)
    hb = p.get_last_heartbeat()
    rprint({"heartbeat": hb, "sqlite": str(settings.sqlite_path), "mode": settings.mode.value})


@app.command("cancel-all")
def cancel_all_cmd() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    if not settings.enable_live_trading:
        rprint("[yellow]ENABLE_LIVE_TRADING is false — refusing to call cancel[/yellow]")
        raise typer.Exit(1)
    clob = ClobWrapper(settings)
    rprint(clob.cancel_all())


@app.command("risk-report")
def risk_report_cmd() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    p = PersistenceService(settings)
    rows = p.recent_risk_events(50)
    t = Table(title="Recent risk events")
    t.add_column("reason")
    t.add_column("message")
    t.add_column("at")
    for r in rows:
        t.add_row(r["reason"], r["message"][:80], r["created_at"])
    rprint(t)
    rep = Path("outputs") / f"daily_report_{date.today().isoformat()}.txt"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text("\n".join(f"{r['created_at']} {r['reason']} {r['message']}" for r in rows))
    rprint(f"Wrote {rep}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
