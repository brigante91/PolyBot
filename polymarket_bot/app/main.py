"""Application entrypoint and run loop with graceful shutdown."""

from __future__ import annotations

import signal
import sys
import time
from typing import TYPE_CHECKING

from app.config import RunMode, load_settings
from app.logger import configure_logging, get_logger

if TYPE_CHECKING:
    pass

_shutdown = False


def _set_shutdown(*_: object) -> None:
    global _shutdown
    _shutdown = True


def run_forever() -> None:
    """Minimal loop: heartbeat until SIGINT/SIGTERM. Multi-market engine: `python -m app.cli run-multi`."""
    settings = load_settings()
    configure_logging(settings.log_level, json_format=True)
    log = get_logger("main")
    signal.signal(signal.SIGINT, _set_shutdown)
    signal.signal(signal.SIGTERM, _set_shutdown)
    log.info("started", mode=settings.mode.value)
    while not _shutdown:
        time.sleep(1)
    log.info("shutdown_complete")


def main() -> None:
    settings = load_settings()
    if settings.mode == RunMode.DRY_RUN:
        configure_logging(settings.log_level)
    run_forever()


if __name__ == "__main__":
    main()
    sys.exit(0)
