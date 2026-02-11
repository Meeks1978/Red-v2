from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ObserverMetrics:
    drift_events: int = 0
    assumption_violations: int = 0
    gate_blocks: int = 0
    override_events: int = 0
    avg_confidence: float = 0.0
    samples: int = 0

    last_run_ms: Optional[int] = None

    # Execute telemetry
    execute_requests: int = 0
    execute_blocks: int = 0
    execute_validation_errors: int = 0
    execute_http_errors: int = 0
    execute_receipt_ok: int = 0
    execute_receipt_fail: int = 0

    execute_blocks_disarmed: int = 0
    execute_blocks_approval: int = 0
    execute_blocks_policy: int = 0
    execute_blocks_other: int = 0

    last_execute_ms: Optional[int] = None
    last_execute_status_code: Optional[int] = None
    last_execute_latency_ms: Optional[int] = None
    last_execute_detail: Optional[str] = None


class ShadowObserver:
    """
    Phase-0 shadow observer.
    Must NEVER raise. Must NOT affect execution.
    """

    def __init__(self, *, enabled: bool = False, interval_sec: int = 60) -> None:
        self.enabled = enabled
        self.interval_sec = interval_sec
        self.metrics = ObserverMetrics()
        self._lock = threading.Lock()

        # optional counters from heartbeat inputs
        self._drift_count = 0
        self._gate_count = 0
        self._override_count = 0

    def tick_heartbeat(
        self,
        *,
        drift_events=None,
        gate_decisions=None,
        trust_surfaces=None,
        override_events: int = 0,
        **kwargs,
    ) -> None:
        """
        Called by hooks/middleware. Accepts optional structured inputs.
        Must NEVER raise, even on unexpected kwargs.
        """
        try:
            if not self.enabled:
                return

            drift_events = drift_events or []
            gate_decisions = gate_decisions or []
            trust_surfaces = trust_surfaces or []

            self._drift_count = len(drift_events)
            self._gate_count = len(gate_decisions)
            self._override_count = int(override_events)

            now_ms = int(time.time() * 1000)
            with self._lock:
                self.metrics.last_run_ms = now_ms

            print({"observer": "shadow", "ts_ms": now_ms})
        except Exception:
            pass

    def record_execute_event(
        self,
        *,
        status_code: int,
        latency_ms: int,
        override_used: bool,
        is_block: bool,
        is_validation_error: bool,
        is_http_error: bool,
        receipt_ok: Optional[bool],
        detail: Optional[str],
        block_kind: Optional[str] = None,
    ) -> None:
        """
        Event-driven telemetry (called by middleware).
        """
        try:
            if not self.enabled:
                return

            now_ms = int(time.time() * 1000)
            d = (detail or "")[:280] if detail else None

            with self._lock:
                self.metrics.execute_requests += 1
                self.metrics.last_execute_ms = now_ms
                self.metrics.last_execute_status_code = int(status_code)
                self.metrics.last_execute_latency_ms = int(latency_ms)
                self.metrics.last_execute_detail = d

                if override_used:
                    self.metrics.override_events += 1

                if is_validation_error:
                    self.metrics.execute_validation_errors += 1
                    self.metrics.gate_blocks += 1

                if is_http_error:
                    self.metrics.execute_http_errors += 1
                    self.metrics.gate_blocks += 1

                if is_block:
                    self.metrics.execute_blocks += 1
                    self.metrics.gate_blocks += 1

                    kind = (block_kind or "other").lower()
                    if kind == "disarmed":
                        self.metrics.execute_blocks_disarmed += 1
                    elif kind == "approval":
                        self.metrics.execute_blocks_approval += 1
                    elif kind == "policy":
                        self.metrics.execute_blocks_policy += 1
                    else:
                        self.metrics.execute_blocks_other += 1

                if receipt_ok is True:
                    self.metrics.execute_receipt_ok += 1
                elif receipt_ok is False:
                    self.metrics.execute_receipt_fail += 1

            print({
                "observer": "shadow",
                "event": "execute",
                "ts_ms": now_ms,
                "status": status_code,
                "latency_ms": latency_ms,
                "override": override_used,
                "block": is_block,
                "validation_error": is_validation_error,
                "http_error": is_http_error,
                "receipt_ok": receipt_ok,
                "block_kind": block_kind,
            })
        except Exception:
            pass
