from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from red.app.types.core import Confidence, Receipt


@dataclass
class IntentOutcomeRecord:
    intent_id: str
    plan_id: Optional[str] = None
    step_receipts: List[Receipt] = field(default_factory=list)
    final_state: Dict[str, Any] = field(default_factory=dict)
    success: Optional[bool] = None
    confidence: Confidence = Confidence(0.5, "unscored")
    postmortem: str = ""


class IntentOutcomeTracker:
    """
    Canonical closure object:
      intent -> plan -> step receipts -> final state -> success -> reflection
    """
    def __init__(self) -> None:
        self._records: Dict[str, IntentOutcomeRecord] = {}

    def start(self, intent_id: str) -> IntentOutcomeRecord:
        rec = IntentOutcomeRecord(intent_id=intent_id)
        self._records[intent_id] = rec
        return rec

    def link_plan(self, intent_id: str, plan_id: str) -> None:
        self._records.setdefault(intent_id, IntentOutcomeRecord(intent_id=intent_id)).plan_id = plan_id

    def add_receipt(self, intent_id: str, receipt: Receipt) -> None:
        self._records.setdefault(intent_id, IntentOutcomeRecord(intent_id=intent_id)).step_receipts.append(receipt)

    def set_final_state(self, intent_id: str, final_state: Dict[str, Any]) -> None:
        self._records.setdefault(intent_id, IntentOutcomeRecord(intent_id=intent_id)).final_state = final_state

    def set_result(self, intent_id: str, success: bool, confidence: Confidence, postmortem: str = "") -> None:
        rec = self._records.setdefault(intent_id, IntentOutcomeRecord(intent_id=intent_id))
        rec.success = success
        rec.confidence = confidence
        rec.postmortem = postmortem

    def get(self, intent_id: str) -> Optional[IntentOutcomeRecord]:
        return self._records.get(intent_id)


class SuccessCriteriaEvaluator:
    """
    Evaluates SuccessCriteria against final_state + receipts.
    Keep deterministic and auditable.
    """
    def evaluate(self, *, required_signals: List[str], must_not_happen: List[str], final_state: Dict[str, Any]) -> bool:
        signals = set(final_state.get("signals", []))
        for r in required_signals:
            if r not in signals:
                return False
        for b in must_not_happen:
            if b in signals:
                return False
        return True


class PostIntentReflection:
    """
    Generates postmortem and updated confidence.
    No side-effects here; memory updates happen in Memory Curator.
    """
    def reflect(self, *, success: bool, receipts: List[Receipt], final_state: Dict[str, Any]) -> tuple[Confidence, str]:
        if success:
            conf = Confidence(0.85, "success criteria satisfied")
            note = "Succeeded. Receipts indicate expected signals were produced."
        else:
            # downweight confidence when receipts show errors
            had_error = any((not r.ok) for r in receipts)
            score = 0.35 if had_error else 0.45
            rationale = "failure with execution errors" if had_error else "failure without explicit execution error"
            conf = Confidence(score, rationale)
            note = "Failed. Inspect receipts and final_state for missing signals or blocked gates."
        return conf, note
