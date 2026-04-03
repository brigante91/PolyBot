"""Application settings with pydantic-settings and live-trading gates."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunMode(str, Enum):
    PAPER = "paper"
    DRY_RUN = "dry_run"
    LIVE = "live"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Hosts
    polymarket_host: str = Field(default="https://clob.polymarket.com", alias="POLYMARKET_HOST")
    gamma_host: str = Field(default="https://gamma-api.polymarket.com", alias="GAMMA_HOST")
    polygon_chain_id: int = Field(default=137, alias="POLYGON_CHAIN_ID")
    # TODO: confirm base URL in official Data API docs; adapter may need path updates.
    data_api_base: str = Field(
        default="https://data-api.polymarket.com",
        alias="DATA_API_BASE",
    )

    # Secrets (never hardcode; empty in paper/public-data-only)
    private_key: str = Field(default="", alias="PRIVATE_KEY")
    funder_address: str = Field(default="", alias="FUNDER_ADDRESS")
    api_key: str = Field(default="", alias="API_KEY")
    api_secret: str = Field(default="", alias="API_SECRET")
    api_passphrase: str = Field(default="", alias="API_PASSPHRASE")

    # Operational mode
    mode: RunMode = Field(default=RunMode.PAPER, alias="MODE")
    enable_live_trading: bool = Field(default=False, alias="ENABLE_LIVE_TRADING")

    # Kill switch
    kill_switch: bool = Field(default=False, alias="KILL_SWITCH")
    kill_switch_file: Path = Field(default=Path("./data/kill_switch"), alias="KILL_SWITCH_FILE")

    # Risk limits (required for live)
    min_liquidity: float = Field(default=1000.0, alias="MIN_LIQUIDITY")
    max_spread_bps: float = Field(default=300.0, alias="MAX_SPREAD_BPS")
    max_order_size_usd: float = Field(default=25.0, alias="MAX_ORDER_SIZE_USD")
    max_market_exposure_usd: float = Field(default=100.0, alias="MAX_MARKET_EXPOSURE_USD")
    max_total_exposure_usd: float = Field(default=300.0, alias="MAX_TOTAL_EXPOSURE_USD")
    daily_loss_limit_usd: float = Field(default=50.0, alias="DAILY_LOSS_LIMIT_USD")
    max_open_orders: int = Field(default=10, alias="MAX_OPEN_ORDERS")
    data_staleness_seconds: float = Field(default=5.0, alias="DATA_STALENESS_SECONDS")

    max_consecutive_losses: int = Field(default=5, alias="MAX_CONSECUTIVE_LOSSES")
    max_intraday_drawdown_usd: float = Field(default=75.0, alias="MAX_INTRADAY_DRAWDOWN_USD")
    adverse_fill_cooldown_seconds: float = Field(default=300.0, alias="ADVERSE_FILL_COOLDOWN_SECONDS")
    api_error_threshold: int = Field(default=5, alias="API_ERROR_THRESHOLD")

    min_orderbook_depth_usd: float = Field(default=50.0, alias="MIN_ORDERBOOK_DEPTH_USD")
    max_slippage_bps: float = Field(default=50.0, alias="MAX_SLIPPAGE_BPS")

    risk_per_trade_bps_min: float = Field(default=10.0, alias="RISK_PER_TRADE_BPS_MIN")
    risk_per_trade_bps_max: float = Field(default=50.0, alias="RISK_PER_TRADE_BPS_MAX")

    clock_skew_max_seconds: float = Field(default=3.0, alias="CLOCK_SKEW_MAX_SECONDS")

    default_strategy: str = Field(default="market_making_passive", alias="DEFAULT_STRATEGY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    sqlite_path: Path = Field(default=Path("./data/bot.db"), alias="SQLITE_PATH")

    heartbeat_interval_seconds: float = Field(default=30.0, alias="HEARTBEAT_INTERVAL_SECONDS")

    # Paper / backtest
    paper_fee_bps: float = Field(default=20.0, alias="PAPER_FEE_BPS")
    paper_slippage_bps: float = Field(default=10.0, alias="PAPER_SLIPPAGE_BPS")
    paper_assumed_queue_ahead: float = Field(default=100.0, alias="PAPER_ASSUMED_QUEUE_AHEAD")

    http_timeout_seconds: float = Field(default=30.0, alias="HTTP_TIMEOUT_SECONDS")
    http_max_retries: int = Field(default=5, alias="HTTP_MAX_RETRIES")
    rate_limit_per_second: float = Field(default=10.0, alias="RATE_LIMIT_PER_SECOND")

    # --- Multi-market adaptive engine ---
    multi_market_mode: bool = Field(default=True, alias="MULTI_MARKET_MODE")
    universe_max_markets: int = Field(default=200, alias="UNIVERSE_MAX_MARKETS")
    universe_scan_pages: int = Field(default=5, alias="UNIVERSE_SCAN_PAGES")
    max_concurrent_positions: int = Field(default=5, alias="MAX_CONCURRENT_POSITIONS")
    max_open_orders_per_market: int = Field(default=2, alias="MAX_OPEN_ORDERS_PER_MARKET")
    min_time_to_resolution_minutes: float = Field(default=5.0, alias="MIN_TIME_TO_RESOLUTION_MINUTES")
    # If set, reject markets resolving later than this (minutes). None = no upper bound.
    fast_resolution_max_minutes: float | None = Field(default=None, alias="FAST_RESOLUTION_MAX_MINUTES")
    min_volume_24h: float = Field(default=500.0, alias="MIN_VOLUME_24H")
    live_analysis_top_n: int = Field(default=25, alias="LIVE_ANALYSIS_TOP_N")
    score_min_tradable: float = Field(default=0.45, alias="SCORE_MIN_TRADABLE")
    maker_first_post_only: bool = Field(default=True, alias="MAKER_FIRST_POST_ONLY")
    allow_market_orders: bool = Field(default=False, alias="ALLOW_MARKET_ORDERS")
    max_exposure_group_usd: float = Field(default=150.0, alias="MAX_EXPOSURE_GROUP_USD")
    strategy_loss_limit_usd: float = Field(default=30.0, alias="STRATEGY_LOSS_LIMIT_USD")
    orchestrator_interval_seconds: float = Field(default=45.0, alias="ORCHESTRATOR_INTERVAL_SECONDS")

    # WebSocket (V3) — market data without polling for critical path when enabled
    enable_ws: bool = Field(default=False, alias="ENABLE_WS")
    ws_market_url: str = Field(
        default="wss://ws-subscriptions-clob.polymarket.com/ws/market",
        alias="WS_MARKET_URL",
    )
    ws_user_url: str = Field(
        default="wss://ws-subscriptions-clob.polymarket.com/ws/user",
        alias="WS_USER_URL",
    )

    # Optional underlying spot for fair value (REST fallback; RTDS can replace later)
    enable_spot_price_rest: bool = Field(default=False, alias="ENABLE_SPOT_PRICE_REST")
    spot_price_ttl_seconds: float = Field(default=30.0, alias="SPOT_PRICE_TTL_SECONDS")

    # Polymarket RTDS WebSocket (optional; stub URL — enable when credentials/feed documented)
    enable_rtds: bool = Field(default=False, alias="ENABLE_RTDS")
    rtds_ws_url: str = Field(default="", alias="RTDS_WS_URL")

    @field_validator("mode", mode="before")
    @classmethod
    def _mode(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower().strip()
        return v

    @model_validator(mode="after")
    def _live_gates(self) -> Settings:
        if self.mode == RunMode.LIVE or self.enable_live_trading:
            errs: list[str] = []
            if not self.enable_live_trading:
                errs.append("ENABLE_LIVE_TRADING must be true for MODE=live")
            if self.mode == RunMode.LIVE and not self.enable_live_trading:
                errs.append("MODE=live requires ENABLE_LIVE_TRADING=true")
            for name, val in [
                ("MAX_ORDER_SIZE_USD", self.max_order_size_usd),
                ("MAX_TOTAL_EXPOSURE_USD", self.max_total_exposure_usd),
                ("DAILY_LOSS_LIMIT_USD", self.daily_loss_limit_usd),
                ("MAX_OPEN_ORDERS", float(self.max_open_orders)),
            ]:
                if val <= 0:
                    errs.append(f"{name} must be positive for live trading")
            if errs:
                raise ValueError("; ".join(errs))
        return self


def load_settings() -> Settings:
    return Settings()
