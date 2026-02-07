from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime

# Scope is the *exact* action that would be allowed later (via Control Plane).
# Red does not execute it. It only proposes and requests approval for it.

class ActionScope(BaseModel):
    runner_id: str = Field(..., description="Target runner id (e.g., ai-laptop).")
    action: str = Field(..., description="Action name (e.g., run_powershell, open_app).")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments for the action.")
    # Optional guardrails for humans:
    human_summary: Optional[str] = Field(None, description="Human readable summary of the action.")
    risk: Literal["low", "medium", "high"] = "medium"


class ApprovalRequest(BaseModel):
    proposal_id: str = Field(..., description="Proposal id from /propose.")
    intent: str = Field(..., description="User intent that created the proposal.")
    scopes: List[ActionScope] = Field(..., min_items=1, description="One or more scoped actions to approve.")
    reason: str = Field("User requested execution; approval required.", description="Why approval is requested.")
    channel: Literal["watch-first", "manual"] = "watch-first"
    # Future: attach device factors, watch presence, voice confidence, etc.
    context: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata for the approval layer.")


class ApprovalToken(BaseModel):
    token_id: str
    issued_at: str
    expires_at: str
    nonce: str

    proposal_id: str
    scopes: List[ActionScope]

    # Integrity
    alg: Literal["HMAC-SHA256"] = "HMAC-SHA256"
    signature: str = Field(..., description="Base64url HMAC over canonical token payload")

    # State
    status: Literal["PENDING", "CONSUMED", "EXPIRED", "REVOKED"] = "PENDING"


class ApprovalVerifyRequest(BaseModel):
    token: ApprovalToken
    # If provided, we additionally verify the token covers this exact scope.
    expected_scope: Optional[ActionScope] = None


class ApprovalVerifyResponse(BaseModel):
    ok: bool
    status: Literal["PENDING", "CONSUMED", "EXPIRED", "REVOKED", "INVALID"]
    reason: str
    expires_at: Optional[str] = None


class ApprovalConsumeRequest(BaseModel):
    token_id: str
    nonce: str


class ApprovalConsumeResponse(BaseModel):
    ok: bool
    status: Literal["CONSUMED", "EXPIRED", "REVOKED", "NOT_FOUND"]
    reason: str
