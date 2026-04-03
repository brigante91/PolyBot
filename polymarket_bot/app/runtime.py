"""Runtime entry for multi-market orchestrator (signal-safe loop)."""

from __future__ import annotations

import signal
import time
from typing import Any

from app.config import RunMode, Settings, load_settings
from app.logger import configure_logging, get_logger
from app.orchestrator import MultiMarketOrchestrator
from app.runtime_control import clear_orchestrator_stop, orchestrator_should_stop, request_orchestrator_stop

log = get_logger("runtime")


def _handle_sig(*_a: Any) -> None:
    request_orchestrator_stop()


def run_multi_market(
    settings: Settings | None = None,
    *,
    mode: RunMode | None = None,
    max_cycles: int | None = None,
) -> None:
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    if not settings.multi_market_mode:
        log.warning("multi_market_disabled", hint="set MULTI_MARKET_MODE=true")
    m = mode or settings.mode
    if m == RunMode.TEST and max_cycles is None:
        max_cycles = 1
    orch = MultiMarketOrchestrator(settings)
    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)
    cycles = 0
    clear_orchestrator_stop()
    try:
        while not orchestrator_should_stop():
            metrics = orch.run_cycle(m)
            log.info("orchestrator_cycle", **metrics.to_dict())
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            if orchestrator_should_stop():
                break
            # Interruptible sleep (TUI quit, tests)
            if settings.orchestrator_interval_seconds <= 0:
                continue
            end = time.monotonic() + float(settings.orchestrator_interval_seconds)
            while time.monotonic() < end:
                if orchestrator_should_stop():
                    break
                time.sleep(min(0.5, end - time.monotonic()))
    finally:
        orch.close()
        log.info("runtime_shutdown", cycles=cycles)
