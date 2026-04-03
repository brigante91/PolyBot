"""Runtime entry for multi-market orchestrator (signal-safe loop)."""

from __future__ import annotations

import signal
import time
from typing import Any

from app.config import RunMode, Settings, load_settings
from app.logger import configure_logging, get_logger
from app.orchestrator import MultiMarketOrchestrator

log = get_logger("runtime")
_stop = False


def _handle_sig(*_a: Any) -> None:
    global _stop
    _stop = True


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
    orch = MultiMarketOrchestrator(settings)
    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)
    cycles = 0
    global _stop
    _stop = False
    try:
        while not _stop:
            metrics = orch.run_cycle(m)
            log.info("orchestrator_cycle", **metrics.to_dict())
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            time.sleep(settings.orchestrator_interval_seconds)
    finally:
        orch.close()
        log.info("runtime_shutdown", cycles=cycles)
