"""Pytest fixtures."""

from __future__ import annotations

import pytest

from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        MODE="paper",
        ENABLE_LIVE_TRADING=False,
        MAX_ORDER_SIZE_USD=25,
        MAX_TOTAL_EXPOSURE_USD=300,
        DAILY_LOSS_LIMIT_USD=50,
        MAX_OPEN_ORDERS=10,
    )
