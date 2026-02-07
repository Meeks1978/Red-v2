from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4
from datetime import datetime, timezone


router = APIRouter()


# ---- Request / Response Models ----

class ProposeRequest(BaseModel):
    intent: str = Field(..., description="What the user wants to accomplish.")
    context: Dict[str, Any] = Field(default_factory=dict, description="Optional structured context.")


class Step(BaseModel):
    step_id: str
    description: str
    runner_id: Optional[str] = None
    action: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)


class ApprovalRequirement(BaseModel):
    required: bool = True
    reason: str = "Execution is gated; approval required for any real-world action."
    channel: Literal["watch-first", "manual", "none"] = "watch-first"


class Proposal(BaseModel):
    proposal_id: str
    created_at: str
    mode: Literal["COPILOT"] = "COPILOT"
    world_state: Literal["DISARMED"] = "DISARMED"

    intent: str
    summary: str
    assumptions: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)

    plan: List[Step]
    approvals: ApprovalRequirement
    next_questions: List[str] = Field(default_factory=list)

    # explicit guarantee: this endpoint never executes
    executed: bool = False
    execution_blocked_reason: str = "Red v2 /propose does not execute. It only returns a proposal."


# ---- Simple heuristic router (placeholder) ----
# This is intentionally dumb & deterministic for now.
# Later we replace this with LLM reasoning + policy checks.

def classify_intent(intent: str) -> Dict[str, Any]:
    text = intent.lower().strip()
    if any(k in text for k in ["run", "execute", "restart", "reboot", "delete", "rm ", "format", "shutdown"]):
        return {"category": "execution", "risk": "high"}
    if any(k in text for k in ["check", "status", "health", "logs", "list", "show"]):
        return {"category": "inspection", "risk": "low"}
    return {"category": "general", "risk": "medium"}


@router.post("/propose", response_model=Proposal)
def propose(req: ProposeRequest) -> Proposal:
    meta = classify_intent(req.intent)

    proposal_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    # Build a plan that is safe-by-default:
    # - inspection steps are described but not executable
    # - any potential execution step is represented as a gated step with no action bound yet
    plan: List[Step] = []

    if meta["category"] == "inspection":
        plan = [
            Step(step_id="S1", description="Gather current system state relevant to the request (no execution)."),
            Step(step_id="S2", description="Summarize findings and recommend next actions (still no execution)."),
        ]
        risks = ["Low risk: read-only intent. Still requires approval before any action."]
        assumptions = ["Target system(s) are reachable over Tailscale.", "Control Plane is the execution authority."]
        next_q = ["Which node(s) should I inspect (ai-control, ai-laptop, ai-simrig, ai-nuc)?"]
        summary = "Read-only proposal: gather facts, summarize, and recommend."
    elif meta["category"] == "execution":
        plan = [
            Step(step_id="S1", description="Confirm exact target and desired outcome (what, where, why)."),
            Step(step_id="S2", description="Generate an execution plan as gated steps (requires explicit approval)."),
            Step(
                step_id="S3",
                description="(GATED) Request approval to execute via Control Plane (no execution performed here).",
                runner_id=None,
                action=None,
                args={"note": "Execution details will be filled only after approval."},
            ),
        ]
        risks = [
            "High risk: request implies execution; must remain DISARMED until explicit approval.",
            "Potential service disruption if executed incorrectly.",
        ]
        assumptions = ["Approval workflow is enabled and watch-first notifications are preferred."]
        next_q = ["Confirm the exact target (service/container/node) and the safe window for changes."]
        summary = "Execution-intent proposal: clarify, plan, and gate behind approval."
    else:
        plan = [
            Step(step_id="S1", description="Clarify objective and constraints."),
            Step(step_id="S2", description="Propose a safe sequence of actions (no execution)."),
        ]
        risks = ["Medium risk: unclear intent. Keep DISARMED until clarified."]
        assumptions = ["You want copilot-first behavior with approvals required."]
        next_q = ["What does success look like, and which systems are in scope?"]
        summary = "General proposal: clarify and propose next steps without executing."

    approvals = ApprovalRequirement(
        required=True,
        reason="Red v2 is DISARMED by default and cannot execute. Approval is required for any execution via Control Plane.",
        channel="watch-first",
    )

    return Proposal(
        proposal_id=proposal_id,
        created_at=created_at,
        intent=req.intent,
        summary=summary,
        assumptions=assumptions,
        risks=risks,
        plan=plan,
        approvals=approvals,
        next_questions=next_q,
    )
