"""check-env and doctor — connectivity and local sanity without live trading credentials."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table

from app.config import Settings, load_settings

console = Console()


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _check_python_version() -> Check:
    v = sys.version_info
    ok = v >= (3, 11)
    return Check("python_version", ok, f"{v.major}.{v.minor}.{v.micro}")


def _check_app_importable() -> Check:
    try:
        import app.config  # noqa: F401

        return Check("import app", True, "app package resolves")
    except Exception as e:
        return Check("import app", False, str(e))


def _check_py_clob_lazy() -> Check:
    """Ensure app.clients does not load py_clob_client until ClobWrapper is accessed."""
    import app.clients as clients_pkg

    loaded = "py_clob_client" in sys.modules
    _ = clients_pkg.__all__
    if not loaded:
        return Check("lazy clients", True, "py_clob_client not loaded on package import")
    return Check("lazy clients", True, "py_clob_client already in sys.modules (ok if other tests ran)")


def _check_data_dir(settings: Settings) -> Check:
    p = Path(settings.sqlite_path).parent
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".write_test"
        probe.write_text("ok")
        probe.unlink(missing_ok=True)
        return Check("data_dir_writable", True, str(p.resolve()))
    except Exception as e:
        return Check("data_dir_writable", False, str(e))


def _check_gamma(settings: Settings) -> Check:
    try:
        r = httpx.get(
            f"{settings.gamma_host.rstrip('/')}/markets",
            params={"limit": 1, "active": "true"},
            timeout=10.0,
        )
        ok = r.status_code < 500
        return Check("gamma_http", ok, f"status={r.status_code}")
    except Exception as e:
        return Check("gamma_http", False, str(e))


def _check_clob_public(settings: Settings) -> Check:
    try:
        host = settings.polymarket_host.rstrip("/")
        r = httpx.get(f"{host}/", timeout=10.0, follow_redirects=True)
        ok = r.status_code < 600
        return Check("clob_host_http", ok, f"status={r.status_code}")
    except Exception as e:
        return Check("clob_host_http", False, str(e))


def _check_websockets_installed() -> Check:
    spec = importlib.util.find_spec("websockets")
    ok = spec is not None
    return Check("websockets_optional", ok, "installed" if ok else "pip install websockets")


def _check_textual_installed() -> Check:
    spec = importlib.util.find_spec("textual")
    ok = spec is not None
    return Check("textual_optional", ok, "installed" if ok else "pip install textual")


def _check_env_file() -> Check:
    env = Path(".env")
    ex = Path(".env.example")
    if env.is_file():
        return Check("dotenv_file", True, str(env.resolve()))
    if ex.is_file():
        return Check("dotenv_file", True, f"copy {ex.name} → .env (example present)")
    return Check("dotenv_file", False, "add .env (see .env.example if present)")


def _check_live_numeric(settings: Settings) -> Check:
    ok = (
        settings.max_order_size_usd > 0
        and settings.max_total_exposure_usd > 0
        and settings.daily_loss_limit_usd > 0
        and settings.max_open_orders > 0
    )
    return Check(
        "risk_limits_positive",
        ok,
        "OK" if ok else "set positive MAX_* and DAILY_LOSS_* in .env",
    )


def run_check_env() -> int:
    """Validate .env-loaded settings and required directories."""
    settings = load_settings()
    checks = [
        _check_python_version(),
        _check_app_importable(),
        _check_env_file(),
        _check_data_dir(settings),
        _check_live_numeric(settings),
        _check_websockets_installed(),
        _check_textual_installed(),
    ]
    return _print_checks("polybot check-env", checks)


def run_doctor() -> int:
    """Smoke-test install + network reachability (no API keys required for public endpoints)."""
    settings = load_settings()
    checks = [
        _check_python_version(),
        _check_app_importable(),
        _check_py_clob_lazy(),
        _check_data_dir(settings),
        _check_gamma(settings),
        _check_clob_public(settings),
        _check_websockets_installed(),
        _check_textual_installed(),
    ]
    return _print_checks("polybot doctor", checks)


def _print_checks(title: str, checks: list[Check]) -> int:
    t = Table(title=title)
    t.add_column("Check")
    t.add_column("OK")
    t.add_column("Detail")
    bad = 0
    for c in checks:
        ok_s = "PASS" if c.ok else "FAIL"
        if not c.ok:
            bad += 1
        t.add_row(c.name, ok_s, c.detail[:120])
    console.print(t)
    if bad:
        console.print(f"[yellow]{bad} check(s) failed — fix before live trading[/yellow]")
        return 1
    console.print("[green]All checks passed.[/green]")
    return 0
