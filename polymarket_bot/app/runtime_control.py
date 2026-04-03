"""Shared stop signal for orchestrator thread (TUI quit, signals)."""

from __future__ import annotations

import threading

_orch_stop = threading.Event()


def request_orchestrator_stop() -> None:
    """Signal the multi-market loop to exit (daemon thread or main)."""
    _orch_stop.set()


def clear_orchestrator_stop() -> None:
    _orch_stop.clear()


def orchestrator_should_stop() -> bool:
    return _orch_stop.is_set()
