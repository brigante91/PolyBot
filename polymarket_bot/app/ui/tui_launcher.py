"""Production entry: `polybot-tui` → control room (optional mode launcher)."""

from __future__ import annotations

from app.logger import configure_logging, get_logger
from app.ui.tui_app import PolyBotTui

log = get_logger("tui_launcher")


def main() -> None:
    """Main entry: launcher + orchestrator thread + control room TUI."""
    from app.config import load_settings

    settings = load_settings()
    configure_logging(settings.log_level)
    PolyBotTui(with_launcher=True).run()


def run_tui_with_launcher() -> None:
    """Alias for tests / explicit launcher."""
    main()
