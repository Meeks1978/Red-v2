from __future__ import annotations
import uuid
from typing import Any, Dict

from app.contracts.intent import IntentEnvelope
from app.contracts.plan import Plan, PlanBundle, PlanStep, SuccessCriteria, PlanVariant

def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

class PlanningEngine:
    def plan(self, intent: IntentEnvelope, ctx: Dict[str, Any]) -> PlanBundle:
        plan_id = _id("plan")
        step = PlanStep(step_id=_id("step"), description="(scaffold) Draft macro steps; no tool binding yet.")
        plan = Plan(
            plan_id=plan_id,
            intent_id=intent.intent_id,
            summary="Scaffold plan",
            assumptions=["(scaffold) World state assumed stable"],
            success=SuccessCriteria(description="Scaffold success criteria"),
            steps=[step],
        )
        variant = PlanVariant(name="default", plan=plan, cost={"risk":"unknown","latency":"unknown"})
        return PlanBundle(selected=plan, variants=[variant], cost_surface={"note":"scaffold"})
