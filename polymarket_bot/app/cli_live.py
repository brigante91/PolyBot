"""Validate .env for live trading before starting orchestrator from TUI."""

from __future__ import annotations

from app.config import Settings


def validate_live_config(settings: Settings) -> tuple[bool, str]:
    """Return (ok, message)."""
    errs: list[str] = []
    if not settings.enable_live_trading:
        errs.append("ENABLE_LIVE_TRADING must be true")
    if settings.max_order_size_usd <= 0:
        errs.append("MAX_ORDER_SIZE_USD must be positive")
    if settings.max_total_exposure_usd <= 0:
        errs.append("MAX_TOTAL_EXPOSURE_USD must be positive")
    if settings.daily_loss_limit_usd <= 0:
        errs.append("DAILY_LOSS_LIMIT_USD must be positive")
    if settings.max_open_orders <= 0:
        errs.append("MAX_OPEN_ORDERS must be positive")
    if not (settings.private_key.strip() and settings.funder_address.strip()):
        errs.append("PRIVATE_KEY and FUNDER_ADDRESS required for live CLOB")
    if not (settings.api_key and settings.api_secret and settings.api_passphrase):
        errs.append("API_KEY, API_SECRET, API_PASSPHRASE required for authenticated endpoints")
    if errs:
        return False, "; ".join(errs)
    return True, "ok"
