from __future__ import annotations

from typing import List, Tuple

from .models import Assumption, IntentRecord, ReasonSurface, SuccessCriteria, new_intent_id, now_iso


def _extract_goal_and_constraints(user_input: str) -> Tuple[str, List[str]]:
    text = user_input.strip()
    parts = [p.strip() for p in text.replace("\n", " ").split(".") if p.strip()]
    if not parts:
        return ("(no goal parsed)", [])
    goal = parts[0]
    constraints = parts[1:]
    return (goal, constraints)


def _extract_assumptions(goal: str, constraints: List[str]) -> List[Assumption]:
    assumptions = []
    if "deploy" in goal.lower():
        assumptions.append(Assumption("Target node is reachable over Tailscale.", False, 0.5))
        assumptions.append(Assumption("Repo working tree is clean or changes are intentional.", False, 0.4))
    if any("latency" in c.lower() or "fast" in c.lower() for c in constraints):
        assumptions.append(Assumption("Latency baseline and budget are known.", False, 0.4))
    return assumptions


def _default_success_criteria(goal: str) -> SuccessCriteria:
    base = [
        "User confirms the answer matches the goal.",
        "Risks or constraints are surfaced.",
        "Next step is explicit."
    ]
    return SuccessCriteria(conditions=base)


def intake(user_input: str, trace_id: str | None = None) -> IntentRecord:
    goal, constraints = _extract_goal_and_constraints(user_input)
    assumptions = _extract_assumptions(goal, constraints)

    reasons = ReasonSurface(
        signals_used=["input:user_message"],
        key_factors=[f"Parsed goal: {goal}"],
        what_would_change_my_mind=["Clarification of scope or constraints may alter plan."]
    )

    rec = IntentRecord(
        intent_id=new_intent_id(),
        created_at=now_iso(),
        updated_at=now_iso(),
        user_input=user_input,
        goal=goal,
        constraints=constraints,
        success=_default_success_criteria(goal),
        assumptions=assumptions,
        confidence=0.65,
        reasons=reasons,
        trace_id=trace_id,
    )
    return rec
