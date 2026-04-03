"""Ensure analysis/clients packages stay import-light (no eager py_clob_client)."""

from __future__ import annotations

import os
from pathlib import Path

import subprocess
import sys

_ROOT = Path(__file__).resolve().parents[1]
_POLY = str(_ROOT / "polymarket_bot")


def _run_isolated(code: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": _POLY}
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_ROOT),
    )


def test_analysis_lazy_getattr() -> None:
    import app.analysis as a

    cls = a.FairValueEngine
    assert cls.__name__ == "FairValueEngine"


def test_clients_package_import_does_not_load_py_clob() -> None:
    """Fresh subprocess: importing app.clients must not load py_clob_client."""
    code = """
import sys
import app.clients
assert "py_clob_client" not in sys.modules, list(sys.modules.keys())
"""
    r = _run_isolated(code)
    assert r.returncode == 0, r.stderr + r.stdout


def test_gamma_client_import_does_not_load_py_clob() -> None:
    """GammaClient path must not pull py-clob-client (only ClobWrapper does)."""
    code = """
import sys
import app.clients
assert "py_clob_client" not in sys.modules
from app.clients import GammaClient
assert GammaClient is not None
assert "py_clob_client" not in sys.modules
"""
    r = _run_isolated(code)
    assert r.returncode == 0, r.stderr + r.stdout


def test_clob_wrapper_import_loads_py_clob() -> None:
    """Sanity: explicit ClobWrapper import is allowed to load SDK."""
    code = """
import sys
from app.clients import ClobWrapper
assert ClobWrapper is not None
assert "py_clob_client" in sys.modules
"""
    r = _run_isolated(code)
    assert r.returncode == 0, r.stderr + r.stdout


def test_cli_health_import() -> None:
    from app.cli_health import run_check_env

    assert callable(run_check_env)
