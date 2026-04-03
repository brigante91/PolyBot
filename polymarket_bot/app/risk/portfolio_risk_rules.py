"""Portfolio-level gates."""

from __future__ import annotations

from app.models.risk import RiskCheckResult
from app.risk.risk_engine import RiskEngine


def check_portfolio(
    risk: RiskEngine,
    *,
    positions_after: int,
    group_exposure_usd: float,
    strategy_id: str,
    category: str | None,
) -> RiskCheckResult:
    return risk.check_portfolio_constraints(
        new_positions_after=positions_after,
        category=category,
        group_exposure_usd=group_exposure_usd,
        strategy_id=strategy_id,
    )
