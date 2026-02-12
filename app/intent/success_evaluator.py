from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from app.intent.outcome_tracker import SuccessCriteria


@dataclass(frozen=True)
class EvalResult:
    ok: bool
    missing_required: List[str]
    violated_forbidden: List[str]
    notes: str


class SuccessCriteriaEvaluator:
    """
    Deterministic evaluator:
    - required_signals must be present/truthy in final_state
    - must_not_happen must be absent or falsy in final_state
    """
    def evaluate(self, *, criteria: SuccessCriteria, final_state: Dict[str, Any]) -> EvalResult:
        missing = []
        violated = []

        for k in criteria.required_signals:
            v = final_state.get(k)
            if not v:
                missing.append(k)

        for k in criteria.must_not_happen:
            v = final_state.get(k)
            if v:
                violated.append(k)

        ok = (len(missing) == 0) and (len(violated) == 0)
        notes = f"missing_required={missing} violated_forbidden={violated}"
        return EvalResult(ok=ok, missing_required=missing, violated_forbidden=violated, notes=notes)
