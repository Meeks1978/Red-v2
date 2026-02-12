from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class SuccessCriteria:
    description: str
    required_signals: List[str] = field(default_factory=list)
    must_not_happen: List[str] = field(default_factory=list)


@dataclass
class IntentRecord:
    intent_id: str
    trace_id: str
    text: str
    created_at_ms: int
    criteria: SuccessCriteria
    # lifecycle
    closed_at_ms: Optional[int] = None
    success: Optional[bool] = None
    confidence: Optional[float] = None
    postmortem: Optional[str] = None
    # evidence
    receipts: List[Dict[str, Any]] = field(default_factory=list)
    final_state: Dict[str, Any] = field(default_factory=dict)


class IntentOutcomeTracker:
    """
    Minimal closure tracker. Stored in-memory (process) and also written to BU-3 memory on close.
    """
    def __init__(self) -> None:
        self._records: Dict[str, IntentRecord] = {}

    def start(self, *, intent_id: str, trace_id: str, text: str, criteria: SuccessCriteria) -> IntentRecord:
        rec = IntentRecord(
            intent_id=intent_id,
            trace_id=trace_id,
            text=text,
            created_at_ms=now_ms(),
            criteria=criteria,
        )
        self._records[intent_id] = rec
        return rec

    def attach_receipt(self, intent_id: str, receipt: Dict[str, Any]) -> None:
        rec = self._records.get(intent_id)
        if not rec:
            return
        rec.receipts.append(receipt)

    def close(
        self,
        *,
        intent_id: str,
        success: bool,
        confidence: float,
        postmortem: str,
        final_state: Dict[str, Any],
    ) -> Optional[IntentRecord]:
        rec = self._records.get(intent_id)
        if not rec:
            return None
        rec.closed_at_ms = now_ms()
        rec.success = bool(success)
        rec.confidence = float(confidence)
        rec.postmortem = postmortem
        rec.final_state = final_state or {}
        return rec

    def get(self, intent_id: str) -> Optional[IntentRecord]:
        return self._records.get(intent_id)
