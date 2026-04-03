"""Risk check types."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class RejectReason(str, Enum):
    OK = "ok"
    KILL_SWITCH = "kill_switch"
    LIVE_DISABLED = "live_disabled"
    STALE_DATA = "stale_data"
    SPREAD_TOO_WIDE = "spread_too_wide"
    ILLIQUID = "illiquid"
    MAX_ORDER_SIZE = "max_order_size"
    MAX_MARKET_EXPOSURE = "max_market_exposure"
    MAX_TOTAL_EXPOSURE = "max_total_exposure"
    DAILY_LOSS = "daily_loss_limit"
    MAX_OPEN_ORDERS = "max_open_orders"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    INTRADAY_DRAWDOWN = "intraday_drawdown"
    COOLDOWN = "cooldown"
    API_UNSTABLE = "api_unstable"
    DEPTH_INSUFFICIENT = "depth_insufficient"
    SLIPPAGE = "slippage"
    DUPLICATE_ORDER = "duplicate_order"
    NO_AVERAGING_DOWN = "no_averaging_down"
    INVENTORY_LIMIT = "inventory_limit"
    MAX_CONCURRENT_POSITIONS = "max_concurrent_positions"
    GROUP_EXPOSURE_LIMIT = "group_exposure_limit"
    STRATEGY_LOSS_LIMIT = "strategy_loss_limit"
    OTHER = "other"


class RiskCheckResult(BaseModel):
    allowed: bool
    reason: RejectReason = RejectReason.OK
    message: str = ""
