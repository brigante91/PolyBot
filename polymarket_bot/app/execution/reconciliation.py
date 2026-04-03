"""Reconcile full order lifecycle: intent → sent → ack → partial/total fill; recovery hooks."""

from __future__ import annotations

import threading
from collections import deque
from typing import TYPE_CHECKING, Any

from app.logger import get_logger
from app.models.order_lifecycle import OrderLifecycle
from app.services.execution_service import ExecutionResult
from app.services.persistence_service import PersistenceService

if TYPE_CHECKING:
    from app.monitor.advanced_metrics import AdvancedMetrics

log = get_logger("reconciliation")


class ReconciliationService:
    def __init__(
        self,
        persistence: PersistenceService,
        *,
        metrics: AdvancedMetrics | None = None,
    ) -> None:
        self._p = persistence
        self._metrics = metrics
        self._lock = threading.Lock()
        self._by_oid: dict[str, dict[str, Any]] = {}
        self._mismatch_log: deque[str] = deque(maxlen=500)

    def record_intent(self, order_key: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._by_oid[order_key] = {
                "lifecycle": OrderLifecycle.INTENT.value,
                "payload": payload,
            }
        log.info("recon_intent", order_key=order_key)

    def record_sent(self, order_key: str, response: dict[str, Any]) -> None:
        oid = str(response.get("orderID") or response.get("id") or order_key)
        with self._lock:
            row = self._by_oid.get(order_key, {})
            row["lifecycle"] = OrderLifecycle.SENT.value
            row["response"] = response
            row["server_order_id"] = oid
            self._by_oid[order_key] = row
            self._by_oid[oid] = row
        log.info("recon_sent", order_id=oid)

    def record_ws_order_event(self, msg: dict[str, Any]) -> None:
        """User WS order event: PLACEMENT / UPDATE / CANCELLATION."""
        et = str(msg.get("type", "")).upper()
        oid = str(msg.get("id", ""))
        if not oid:
            return
        with self._lock:
            row = self._by_oid.get(oid, {})
            if et == "PLACEMENT":
                row["lifecycle"] = OrderLifecycle.ACK.value
            elif et == "UPDATE":
                row["lifecycle"] = OrderLifecycle.PARTIAL_FILL.value
            elif et == "CANCELLATION":
                row["lifecycle"] = OrderLifecycle.CANCELLED.value
                if self._metrics:
                    self._metrics.record_cancel()
            row["ws_order"] = msg
            self._by_oid[oid] = row
        log.info("recon_ws_order", oid=oid, type=et)

    def record_ws_trade(self, msg: dict[str, Any]) -> None:
        st = str(msg.get("status", "")).upper()
        oid = str(msg.get("id", ""))
        with self._lock:
            row = self._by_oid.get(oid, {})
            if st in ("CONFIRMED",):
                row["lifecycle"] = OrderLifecycle.FILLED.value
                if self._metrics:
                    maker = bool(msg.get("maker", msg.get("isMaker", True)))
                    self._metrics.record_fill(maker=maker)
            elif st == "FAILED":
                row["lifecycle"] = OrderLifecycle.REJECTED.value
            row["ws_trade"] = msg
            self._by_oid[oid] = row
        log.info("recon_ws_trade", oid=oid, status=st)

    def record_mismatch(self, detail: str) -> None:
        self._mismatch_log.append(detail)
        log.warning("recon_mismatch", detail=detail)
        self._p.insert_risk_event("recon_mismatch", detail, {})

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"orders_tracked": len(self._by_oid), "recent_mismatches": list(self._mismatch_log)[-10:]}

    def record_execution(
        self,
        *,
        market_id: str,
        strategy_id: str,
        res: ExecutionResult,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload = {"market_id": market_id, "strategy_id": strategy_id, "ok": res.ok, "reason": res.reason.value}
        if extra:
            payload.update(extra)
        log.info("recon_execution", **payload)
        if not res.ok:
            self._p.insert_risk_event(res.reason.value, res.message, payload)
