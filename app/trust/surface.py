from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.types.core import Confidence
from app.governance.assumptions import Assumption, AssumptionStatus
from app.governance.uncertainty_gate import GateDecision
from app.world.drift import DriftEvent


@dataclass(frozen=True)
class ReasonSurface:
    """
    Canonical human-facing explanation artifact.
    """
    reason: str
    confidence: Confidence
    violated_assumptions: List[str]
    drift_keys: List[str]
    what_would_change_my_mind: List[str]


class TrustSurfaceBuilder:
    """
    Builds a ReasonSurface from governance + world signals.
    """

    def build(
        self,
        *,
        base_reason: str,
        base_confidence: Confidence,
        assumptions: Optional[List[Assumption]] = None,
        drift_events: Optional[List[DriftEvent]] = None,
        gate_decision: Optional[GateDecision] = None,
    ) -> ReasonSurface:

        violated = [
            a.key for a in (assumptions or [])
            if a.status == AssumptionStatus.VIOLATED
        ]

        drift_keys = [d.key for d in (drift_events or [])]

        reason_parts = [base_reason]

        if violated:
            reason_parts.append(
                f"Assumptions violated: {violated}"
            )

        if drift_keys:
            reason_parts.append(
                f"World drift detected on: {drift_keys}"
            )

        if gate_decision and not gate_decision.allowed:
            reason_parts.append(
                f"Blocked by governance: {gate_decision.reason}"
            )

        final_reason = " | ".join(reason_parts)

        what_changes = []
        if violated:
            what_changes.append("Restore violated assumptions")
        if drift_keys:
            what_changes.append("Update world state to match expectations")
        if gate_decision and not gate_decision.allowed:
            what_changes.append("Explicit human override")

        return ReasonSurface(
            reason=final_reason,
            confidence=gate_decision.confidence if gate_decision else base_confidence,
            violated_assumptions=violated,
            drift_keys=drift_keys,
            what_would_change_my_mind=what_changes,
        )
