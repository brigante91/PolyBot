"""Ensure analysis/clients packages stay import-light (no eager py_clob_client)."""

from __future__ import annotations

import os
from pathlib import Path

import subprocess
import sys

_ROOT = Path(__file__).resolve().parents[1]
_POLY = str(_ROOT / "polymarket_bot")


def test_analysis_lazy_getattr() -> None:
    import app.analysis as a

    cls = a.FairValueEngine
    assert cls.__name__ == "FairValueEngine"


def test_clients_lazy_no_clob_until_used() -> None:
    code = """
import sys
import app.clients
assert "py_clob_client" not in sys.modules
from app.clients import GammaClient
assert GammaClient is not None
"""
    env = {**os.environ, "PYTHONPATH": _POLY}
    r = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_ROOT),
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_cli_health_import() -> None:
    from app.cli_health import run_check_env

    # May fail if data dir not writable in sandbox — still importable
    assert callable(run_check_env)
