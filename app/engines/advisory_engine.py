from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.contracts.intent import Intent, Plan, SuccessCriteria
from app.services.intent_outcome import (
    IntentOutcomeTracker,
    SuccessCriteriaEvaluator,
    PostIntentReflection,
)
from app.trust.surface import TrustSurfaceBuilder, ReasonSurface
from app.types.core import Confidence

# BU-2 imports
from app.governance.assumptions import Assumption
from app.governance.assumption_verifier import AssumptionVerifier
from app.governance.uncertainty_gate import UncertaintyGate, GateDecision
from app.world.drift import DriftEvent


@dataclass
class AdvisoryResult:
    intent_id: str
    plan_id: Optional[str]
    success: Optional[bool]
    trust: ReasonSurface
    debug: Dict[str, Any]


class AdvisoryEngine:
    """
    Read-only (no execution). Creates closure records, trust surfaces,
    and applies governance uncertainty gates.
    """

    def __init__(
        self,
        *,
        tracker: IntentOutcomeTracker,
        evaluator: SuccessCriteriaEvaluator,
        reflector: PostIntentReflection,
        trust_builder: TrustSurfaceBuilder,
    ) -> None:
        self.tracker = tracker
        self.evaluator = evaluator
        self.reflector = reflector
        self.trust_builder = trust_builder

    # ----------------------------
    # BU-1 — Intent lifecycle
    # ----------------------------
    def start_intent(self, intent: Intent) -> None:
        self.tracker.start(intent.intent_id)

    def attach_plan(self, plan: Plan) -> None:
        self.tracker.link_plan(plan.intent_id, plan.plan_id)

    def close_intent(
        self,
        *,
        intent_id: str,
        success_criteria: SuccessCriteria,
        final_state: Dict[str, Any],
    ) -> AdvisoryResult:
        rec = self.tracker.get(intent_id)
        receipts = rec.step_receipts if rec else []

        ok = self.evaluator.evaluate(
            required_signals=success_criteria.required_signals,
            must_not_happen=success_criteria.must_not_happen,
            final_state=final_state,
        )

        conf, post = self.reflector.reflect(
            success=ok,
            receipts=receipts,
            final_state=final_state,
        )

        self.tracker.set_final_state(intent_id, final_state)
        self.tracker.set_result(intent_id, ok, conf, postmortem=post)

        # IMPORTANT:
        # BU-1 uses trust surface WITHOUT governance context
        trust = self.trust_builder.build(
            base_reason=post,
            base_confidence=conf,
            assumptions=[],
            drift_events=[],
            gate_decision=None,
        )

        return AdvisoryResult(
            intent_id=intent_id,
            plan_id=(rec.plan_id if rec else None),
            success=ok,
            trust=trust,
            debug={
                "final_state": final_state,
                "receipt_count": len(receipts),
            },
        )

    # ----------------------------
    # BU-2 — Governance gate
    # ----------------------------
    def apply_uncertainty_governance(
        self,
        *,
        assumptions: list[Assumption],
        drift_events: list[DriftEvent],
        confidence: Confidence,
    ) -> GateDecision:
        verifier = AssumptionVerifier()
        gate = UncertaintyGate()

        verified = verifier.verify(
            assumptions=assumptions,
            drift_events=drift_events,
        )

        return gate.decide(
            assumptions=verified,
            confidence=confidence,
        )

    # ----------------------------
    # TRUST SURFACE (BU-2 / BU-4)
    # ----------------------------
    def build_trust_surface(
        self,
        *,
        base_reason: str,
        base_confidence: Confidence,
        assumptions: list[Assumption],
        drift_events: list[DriftEvent],
        gate_decision: GateDecision,
    ) -> ReasonSurface:
        return self.trust_builder.build(
            base_reason=base_reason,
            base_confidence=base_confidence,
            assumptions=assumptions,
            drift_events=drift_events,
            gate_decision=gate_decision,
        )
