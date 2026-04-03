"""Append-only JSONL session log for replay and audit."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.logger import get_logger

log = get_logger("session_recorder")


class SessionRecorder:
    """Writes one JSON object per line: cycle snapshots, decisions, optional WS events."""

    def __init__(self, path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._path = path
        self._fh: Any = None

    def open_default(self, base_dir: Path | None = None) -> None:
        base = base_dir or Path("./data/sessions")
        base.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._path = base / f"session_{ts}.jsonl"
        self._fh = self._path.open("a", encoding="utf-8")
        log.info("session_recorder_open", path=str(self._path))

    def close(self) -> None:
        with self._lock:
            if self._fh:
                self._fh.close()
                self._fh = None

    def record(self, record_type: str, payload: dict[str, Any]) -> None:
        if not self._fh:
            return
        line = json.dumps(
            {"t": time.time(), "type": record_type, **payload},
            default=str,
        )
        with self._lock:
            self._fh.write(line + "\n")
            self._fh.flush()
