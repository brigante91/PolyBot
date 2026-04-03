from __future__ import annotations

from app.risk.risk_engine import RiskEngine


def health_snapshot(risk: RiskEngine) -> dict[str, object]:
    return {
        "api_errors": risk.state.consecutive_api_errors,
        "open_positions": risk.state.open_position_count,
    }
