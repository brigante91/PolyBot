"""Global kill switch: env KILL_SWITCH and optional file flag."""

from __future__ import annotations

from pathlib import Path

from app.config import Settings


class KillSwitch:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_active(self) -> bool:
        if self._settings.kill_switch:
            return True
        path = Path(self._settings.kill_switch_file)
        try:
            return path.exists()
        except OSError:
            return False
