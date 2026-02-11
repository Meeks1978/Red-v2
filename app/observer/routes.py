from __future__ import annotations

from fastapi import APIRouter
from app.services.container import ServiceContainer

router = APIRouter(prefix="/observer", tags=["observer"])


@router.get("/metrics")
def observer_metrics():
    m = ServiceContainer.shadow_observer.metrics
    return {
        "enabled": ServiceContainer.shadow_observer.enabled,
        "interval_sec": ServiceContainer.shadow_observer.interval_sec,
        "metrics": {
            # existing
            "drift_events": m.drift_events,
            "assumption_violations": m.assumption_violations,
            "gate_blocks": m.gate_blocks,
            "override_events": m.override_events,
            "avg_confidence": m.avg_confidence,
            "samples": m.samples,
            "last_run_ms": m.last_run_ms,

            # execute telemetry
            "execute_requests": m.execute_requests,
            "execute_blocks": m.execute_blocks,
            "execute_validation_errors": m.execute_validation_errors,
            "execute_http_errors": m.execute_http_errors,
            "execute_receipt_ok": m.execute_receipt_ok,
            "execute_receipt_fail": m.execute_receipt_fail,

            # block classifications
            "execute_blocks_disarmed": m.execute_blocks_disarmed,
            "execute_blocks_approval": m.execute_blocks_approval,
            "execute_blocks_policy": m.execute_blocks_policy,
            "execute_blocks_other": m.execute_blocks_other,

            # last execute snapshot
            "last_execute_ms": m.last_execute_ms,
            "last_execute_status_code": m.last_execute_status_code,
            "last_execute_latency_ms": m.last_execute_latency_ms,
            "last_execute_detail": m.last_execute_detail,
        },
    }
