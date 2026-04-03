"""Central risk checks before any order."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.config import RunMode, Settings
from app.models.order import OrderIntent
from app.models.orderbook import OrderBookSnapshot
from app.models.risk import RejectReason, RiskCheckResult
from app.risk.exposure_limits import ExposureLimits, ExposureState
from app.risk.kill_switch import KillSwitch
from app.risk.position_sizer import PositionSizer
from app.utils.time import utc_now


@dataclass
class RiskEngineState:
    exposure: ExposureState = field(default_factory=ExposureState)
    day_start_pnl: float = 0.0
    realized_today: float = 0.0
    peak_intraday_equity: float = 0.0
    consecutive_losses: int = 0
    consecutive_api_errors: int = 0
    last_adverse_fill_at: datetime | None = None
    last_order_hashes: dict[str, float] = field(default_factory=dict)
    open_position_count: int = 0
    strategy_realized_pnl: dict[str, float] = field(default_factory=dict)


class RiskEngine:
    """Independent risk gate — strategies and execution must consult this."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._kill = KillSwitch(settings)
        self._exposure = ExposureLimits(settings)
        self._sizer = PositionSizer(settings)
        self.state = RiskEngineState()
        self._last_day: object | None = None

    def reset_intraday_if_needed(self, now: datetime | None = None) -> None:
        now = now or utc_now()
        # Simple UTC day boundary
        if self._last_day != now.date():
            self._last_day = now.date()
            self.state.realized_today = 0.0
            self.state.consecutive_losses = 0
            self.state.day_start_pnl = 0.0

    def register_api_error(self) -> None:
        self.state.consecutive_api_errors += 1

    def register_api_success(self) -> None:
        self.state.consecutive_api_errors = 0

    def check_pre_trade(
        self,
        intent: OrderIntent,
        *,
        mode: RunMode,
        book: OrderBookSnapshot | None,
        notional_usd: float,
        is_adding_to_loser: bool,
    ) -> RiskCheckResult:
        if self._kill.is_active():
            return RiskCheckResult(allowed=False, reason=RejectReason.KILL_SWITCH, message="kill_switch")

        if mode == RunMode.LIVE and not self._settings.enable_live_trading:
            return RiskCheckResult(allowed=False, reason=RejectReason.LIVE_DISABLED, message="live_disabled")

        if self.state.consecutive_api_errors >= self._settings.api_error_threshold:
            return RiskCheckResult(allowed=False, reason=RejectReason.API_UNSTABLE, message="api_unstable")

        if book:
            age = (utc_now() - book.fetched_at.replace(tzinfo=book.fetched_at.tzinfo or timezone.utc)).total_seconds()
            if age > self._settings.data_staleness_seconds:
                return RiskCheckResult(allowed=False, reason=RejectReason.STALE_DATA, message="stale_book")

            sp = book.spread_bps()
            if sp is not None and sp > self._settings.max_spread_bps:
                return RiskCheckResult(allowed=False, reason=RejectReason.SPREAD_TOO_WIDE, message="spread")

            depth_usd = self._estimate_depth_usd(book)
            if depth_usd < self._settings.min_orderbook_depth_usd:
                return RiskCheckResult(allowed=False, reason=RejectReason.ILLIQUID, message="depth")

        if notional_usd > self._settings.max_order_size_usd:
            return RiskCheckResult(allowed=False, reason=RejectReason.MAX_ORDER_SIZE, message="max_order")

        if self._exposure.would_exceed_market(self.state.exposure, intent.market_id, notional_usd):
            return RiskCheckResult(allowed=False, reason=RejectReason.MAX_MARKET_EXPOSURE, message="market")

        if self._exposure.would_exceed_total(self.state.exposure, notional_usd):
            return RiskCheckResult(allowed=False, reason=RejectReason.MAX_TOTAL_EXPOSURE, message="total")

        if self.state.realized_today <= -abs(self._settings.daily_loss_limit_usd):
            return RiskCheckResult(allowed=False, reason=RejectReason.DAILY_LOSS, message="daily_loss")

        if self.state.consecutive_losses >= self._settings.max_consecutive_losses:
            return RiskCheckResult(allowed=False, reason=RejectReason.CONSECUTIVE_LOSSES, message="losses")

        dd = self._intraday_drawdown()
        if dd >= self._settings.max_intraday_drawdown_usd:
            return RiskCheckResult(allowed=False, reason=RejectReason.INTRADAY_DRAWDOWN, message="drawdown")

        if self._exposure.max_open_orders_exceeded(self.state.exposure):
            return RiskCheckResult(allowed=False, reason=RejectReason.MAX_OPEN_ORDERS, message="open_orders")

        if self._in_adverse_cooldown():
            return RiskCheckResult(allowed=False, reason=RejectReason.COOLDOWN, message="cooldown")

        if is_adding_to_loser:
            return RiskCheckResult(allowed=False, reason=RejectReason.NO_AVERAGING_DOWN, message="no_avg_down")

        return RiskCheckResult(allowed=True, reason=RejectReason.OK)

    def check_portfolio_constraints(
        self,
        *,
        new_positions_after: int,
        category: str | None,
        group_exposure_usd: float,
        strategy_id: str,
    ) -> RiskCheckResult:
        """Second-level checks: concurrent positions, group exposure, per-strategy loss."""
        if new_positions_after > self._settings.max_concurrent_positions:
            return RiskCheckResult(
                allowed=False,
                reason=RejectReason.MAX_CONCURRENT_POSITIONS,
                message="max_concurrent_positions",
            )
        if group_exposure_usd > self._settings.max_exposure_group_usd:
            return RiskCheckResult(
                allowed=False,
                reason=RejectReason.GROUP_EXPOSURE_LIMIT,
                message="group_exposure",
            )
        strat_pnl = self.state.strategy_realized_pnl.get(strategy_id, 0.0)
        if strat_pnl <= -abs(self._settings.strategy_loss_limit_usd):
            return RiskCheckResult(
                allowed=False,
                reason=RejectReason.STRATEGY_LOSS_LIMIT,
                message="strategy_loss",
            )
        _ = category
        return RiskCheckResult(allowed=True, reason=RejectReason.OK)

    def _estimate_depth_usd(self, book: OrderBookSnapshot) -> float:
        bb, ba = book.best_bid, book.best_ask
        mid = book.mid()
        if mid is None or mid <= 0:
            return 0.0
        bid_sz = book.bids[0].size if book.bids else 0.0
        ask_sz = book.asks[0].size if book.asks else 0.0
        return (bid_sz + ask_sz) * mid

    def _intraday_drawdown(self) -> float:
        peak = self.state.peak_intraday_equity
        eq = self.state.day_start_pnl + self.state.realized_today
        if eq > peak:
            self.state.peak_intraday_equity = eq
            peak = eq
        return peak - eq

    def _in_adverse_cooldown(self) -> bool:
        if self.state.last_adverse_fill_at is None:
            return False
        elapsed = (utc_now() - self.state.last_adverse_fill_at).total_seconds()
        return elapsed < self._settings.adverse_fill_cooldown_seconds

    def suggest_size(
        self,
        *,
        bankroll_usd: float,
        confidence: float,
        spread_bps: float | None,
        mid_price: float | None,
    ) -> float:
        return self._sizer.size_usd(
            bankroll_usd=bankroll_usd,
            confidence=confidence,
            spread_bps=spread_bps,
            mid_price=mid_price,
        )
