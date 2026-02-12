from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import time
import uuid


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class IntentRecord:
    """
    Minimal durable intent record.
    This is intentionally conservative and does not depend on any other modules.
    """
    intent_id: str
    trace_id: str
    text: str
    created_at_ms: int
    updated_at_ms: int

    status: str = "open"  # open|closed
    ok: Optional[bool] = None
    summary: Optional[str] = None
    confidence: Optional[float] = None
    postmortem: Optional[str] = None

    required_signals: List[str] = None
    must_not_happen: List[str] = None

    final_state: Dict[str, Any] = None
    receipts: List[Dict[str, Any]] = None
    evaluation: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # dataclasses default handling
        d["required_signals"] = d["required_signals"] or []
        d["must_not_happen"] = d["must_not_happen"] or []
        d["final_state"] = d["final_state"] or {}
        d["receipts"] = d["receipts"] or []
        d["evaluation"] = d["evaluation"] or {}
        return d


class SuccessCriteriaEvaluator:
    """
    Placeholder evaluator. Returns a structured result, but does not enforce policy.
    You can harden this later (BU-2/BU-6), without changing storage.
    """
    def evaluate(
        self,
        *,
        required_signals: List[str],
        must_not_happen: List[str],
        final_state: Dict[str, Any],
        receipts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        required_signals = required_signals or []
        must_not_happen = must_not_happen or []

        missing_required = [s for s in required_signals if not final_state.get(s)]
        violated_forbidden = [s for s in must_not_happen if final_state.get(s)]

        ok = (len(missing_required) == 0) and (len(violated_forbidden) == 0)

        return {
            "ok": ok,
            "missing_required": missing_required,
            "violated_forbidden": violated_forbidden,
            "receipts_count": len(receipts or []),
        }


class PostIntentReflection:
    """
    Placeholder. Produces a short postmortem string and confidence.
    """
    def reflect(self, *, ok: bool, eval_result: Dict[str, Any]) -> Dict[str, Any]:
        if ok:
            return {
                "postmortem": "SUCCESS | missing_required=[] violated_forbidden=[]",
                "confidence": 0.8,
            }
        return {
            "postmortem": f"FAIL | missing_required={eval_result.get('missing_required', [])} "
                          f"violated_forbidden={eval_result.get('violated_forbidden', [])}",
            "confidence": 0.2,
        }


class IntentOutcomeTracker:
    """
    Minimal intent tracker used by /v1/intent/*.
    Uses an internal in-memory map. This unblocks boot deterministically.
    Later you can swap persistence behind this without changing API shape.
    """
    def __init__(
        self,
        evaluator: Optional[SuccessCriteriaEvaluator] = None,
        reflector: Optional[PostIntentReflection] = None,
    ) -> None:
        self._db: Dict[str, IntentRecord] = {}
        self._evaluator = evaluator or SuccessCriteriaEvaluator()
        self._reflector = reflector or PostIntentReflection()

    def start(
        self,
        *,
        text: str,
        trace_id: Optional[str] = None,
        required_signals: Optional[List[str]] = None,
        must_not_happen: Optional[List[str]] = None,
    ) -> IntentRecord:
        tid = trace_id or f"trace_{uuid.uuid4().hex[:10]}"
        intent_id = f"intent_{uuid.uuid4().hex[:10]}"
        t = now_ms()
        rec = IntentRecord(
            intent_id=intent_id,
            trace_id=tid,
            text=text,
            created_at_ms=t,
            updated_at_ms=t,
            required_signals=required_signals or [],
            must_not_happen=must_not_happen or [],
            final_state={},
            receipts=[],
            evaluation={},
        )
        self._db[intent_id] = rec
        return rec

    def close(
        self,
        *,
        intent_id: str,
        ok: bool,
        final_state: Optional[Dict[str, Any]] = None,
        receipts: Optional[List[Dict[str, Any]]] = None,
        summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        rec = self._db.get(intent_id)
        if not rec:
            return {"ok": False, "error": "intent_id_not_found", "intent_id": intent_id}

        rec.status = "closed"
        rec.updated_at_ms = now_ms()
        rec.final_state = final_state or {}
        rec.receipts = receipts or []
        rec.summary = summary or rec.summary
        rec.ok = bool(ok)

        eval_result = self._evaluator.evaluate(
            required_signals=rec.required_signals or [],
            must_not_happen=rec.must_not_happen or [],
            final_state=rec.final_state or {},
            receipts=rec.receipts or [],
        )
        rec.evaluation = eval_result
        refl = self._reflector.reflect(ok=rec.ok, eval_result=eval_result)
        rec.postmortem = refl.get("postmortem")
        rec.confidence = float(refl.get("confidence", 0.5))

        return {"ok": True, "intent": rec.to_dict()}

    def open(self, *, limit: int = 20) -> List[Dict[str, Any]]:
        out = [r.to_dict() for r in self._db.values() if r.status == "open"]
        out.sort(key=lambda x: x.get("created_at_ms", 0), reverse=True)
        return out[: max(1, int(limit))]

    def stats(self) -> Dict[str, Any]:
        open_count = sum(1 for r in self._db.values() if r.status == "open")
        closed_count = sum(1 for r in self._db.values() if r.status == "closed")
        ok_count = sum(1 for r in self._db.values() if r.status == "closed" and r.ok is True)
        return {"open": open_count, "closed": closed_count, "ok": ok_count}



# Back-compat alias (older imports expect IntentOutcomeStore)
IntentOutcomeStore = IntentOutcomeTracker
__all__ = [
        "IntentOutcomeStore",
"IntentOutcomeTracker",
    "SuccessCriteriaEvaluator",
    "PostIntentReflection",
    "IntentRecord",
]
