from __future__ import annotations

import time

from app.services.container import ServiceContainer
from app.contracts.intent import Intent, Plan, SuccessCriteria
from app.types.core import new_id


def main() -> None:
    c = ServiceContainer()

    intent = Intent(
        intent_id=new_id("intent"),
        user_text="Draft an email to schedule a meeting",
        created_at_ms=int(time.time() * 1000),
    )
    c.advisory_engine.start_intent(intent)

    plan = Plan(
        plan_id=new_id("plan"),
        intent_id=intent.intent_id,
        summary="Propose email draft + confirm availability",
        assumptions=["User wants a professional tone"],
        success=SuccessCriteria(
            description="Email draft produced without sending",
            required_signals=["email_draft_created"],
            must_not_happen=["email_sent"],
        ),
    )
    c.advisory_engine.attach_plan(plan)

    final_state = {"signals": ["email_draft_created"]}
    result = c.advisory_engine.close_intent(
        intent_id=intent.intent_id,
        success_criteria=plan.success,  # type: ignore[arg-type]
        final_state=final_state,
    )

    print("SUCCESS:", result.success)
    print("CONF:", result.trust.confidence.score, "-", result.trust.confidence.rationale)
    print("WHY:", result.trust.reason)


if __name__ == "__main__":
    main()
