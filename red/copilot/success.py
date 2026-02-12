from __future__ import annotations

from typing import Dict, Tuple

from .models import IntentRecord, IntentStatus, now_iso


def evaluate_success(rec: IntentRecord, assistant_output: str) -> Tuple[IntentStatus, Dict]:
    text = assistant_output.lower()

    has_next = any(k in text for k in ["next step", "step 1", "run:", "create:", "add:"])
    mentions_risk = any(k in text for k in ["risk", "constraint", "tradeoff", "rollback"])

    blocked = any(k in text for k in ["cannot", "blocked", "not possible"])
    if blocked:
        return (IntentStatus.BLOCKED, {"reason": "assistant_signaled_blocked"})

    if has_next and mentions_risk:
        return (IntentStatus.DONE, {"reason": "closure_met"})
    if has_next or mentions_risk:
        return (IntentStatus.PARTIAL, {"reason": "partial_closure"})
    return (IntentStatus.OPEN, {"reason": "no_closure_markers"})


def close_intent(rec: IntentRecord, assistant_output: str) -> IntentRecord:
    status, meta = evaluate_success(rec, assistant_output)
    rec.status = status
    rec.updated_at = now_iso()
    rec.reflection = meta
    return rec
