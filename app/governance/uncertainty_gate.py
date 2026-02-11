from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.governance.assumptions import Assumption, AssumptionStatus
from app.types.core import Confidence


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str
    confidence: Confidence


class UncertaintyGate:
    """
    Blocks execution when assumptions are violated or confidence is too low.
    """
    def decide(
        self,
        *,
        assumptions: List[Assumption],
        confidence: Confidence,
        min_confidence: float = 0.6,
    ) -> GateDecision:
        violated = [a for a in assumptions if a.status == AssumptionStatus.VIOLATED]

        if violated:
            return GateDecision(
                allowed=False,
                reason=f"assumptions violated: {[a.key for a in violated]}",
                confidence=Confidence(
                    score=min(confidence.score, 0.4),
                    rationale="world drift violated plan assumptions",
                ),
            )

        if confidence.score < min_confidence:
            return GateDecision(
                allowed=False,
                reason="confidence below threshold",
                confidence=confidence,
            )

        return GateDecision(
            allowed=True,
            reason="uncertainty gate passed",
            confidence=confidence,
        )
