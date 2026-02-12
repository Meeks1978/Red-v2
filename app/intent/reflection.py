from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class ReflectionResult:
    confidence: float
    postmortem: str


class PostIntentReflection:
    """
    Phase-0 deterministic reflection:
    - base confidence from success/failure
    - penalize if receipts contain errors
    """
    def reflect(self, *, success: bool, receipts: List[Dict[str, Any]], eval_notes: str) -> ReflectionResult:
        base = 0.80 if success else 0.30

        # penalize for explicit receipt errors
        penalty = 0.0
        for r in receipts or []:
            err = str(r.get("error") or "")
            if err:
                penalty += 0.05

        conf = max(0.05, min(0.95, base - penalty))
        pm = f"{'SUCCESS' if success else 'FAIL'} | {eval_notes} | receipt_errors_penalty={penalty:.2f}"
        return ReflectionResult(confidence=conf, postmortem=pm)
