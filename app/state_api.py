from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel, Field

from app.world_state import WorldState, get_state, set_state, arm, disarm, freeze

router = APIRouter(prefix="/v1", tags=["state"])


# ----------------------------
# Models
# ----------------------------

class StateResponse(BaseModel):
    state: str
    reason: str
    updated_at: str
    updated_by: str


class StateSetRequest(BaseModel):
    state: WorldState = Field(...)
    reason: str = Field(..., min_length=1, max_length=500)
    actor: str = Field(default="user", min_length=1, max_length=64)
    trace_id: str | None = Field(default=None, max_length=128)


class ApprovalToken(BaseModel):
    # Match what your /approval/request returns
    token_id: str
    proposal_id: str
    status: str
    issued_at: str  # ISO string
    expires_at: str  # ISO string
    nonce: str
    alg: str
    signature: str
    scopes: List[Dict[str, Any]] = Field(default_factory=list)


class ActivateReq(BaseModel):
    approval_token: ApprovalToken
    reason: str = Field(default="activate", min_length=1, max_length=500)
    actor: str = Field(default="user", min_length=1, max_length=64)
    trace_id: str | None = Field(default=None, max_length=128)


class DeactivateReq(BaseModel):
    approval_token: ApprovalToken
    reason: str = Field(default="deactivate", min_length=1, max_length=500)
    actor: str = Field(default="user", min_length=1, max_length=64)
    trace_id: str | None = Field(default=None, max_length=128)


# ----------------------------
# Helpers
# ----------------------------

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _dev_mode_ok(request: Request, dev_key: Optional[str]) -> None:
    """
    DEV-only guard for /v1/state (generic set).
    Requires:
      - RED_DEV_MODE=true
      - RED_DEV_KEY set
      - header X-Red-Dev-Key matches
      - caller is localhost (fail-closed)
    """
    if not _env_bool("RED_DEV_MODE", False):
        raise HTTPException(status_code=404, detail="Not Found")

    expected = os.getenv("RED_DEV_KEY", "")
    if not expected:
        raise HTTPException(status_code=500, detail="RED_DEV_KEY must be set when RED_DEV_MODE=true")

    client_ip = getattr(getattr(request, "client", None), "host", None)
    if client_ip not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=403, detail="DEV state control restricted to localhost")

    if not dev_key or dev_key != expected:
        raise HTTPException(status_code=403, detail="Invalid dev key")


def _to_ms(x: Any) -> Optional[int]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return int(x)
    if isinstance(x, str):
        xs = x.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(xs)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except Exception:
            try:
                return int(xs)
            except Exception:
                return None
    return None


def _require_token_fresh(token: ApprovalToken) -> None:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    exp_ms = _to_ms(getattr(token, "expires_at", None))
    if exp_ms is not None and exp_ms <= now_ms:
        raise HTTPException(status_code=403, detail="Approval invalid: expired")

    iss_ms = _to_ms(getattr(token, "issued_at", None))
    if iss_ms is not None and iss_ms > now_ms + 5000:
        raise HTTPException(status_code=403, detail="Approval invalid: issued_at in future")


def _require_action_scope(token: ApprovalToken, required_action: str) -> None:
    """
    Your token 'scopes' are ActionScope-like dicts:
      { runner_id, action, args?, human_summary?, risk? }

    So we treat "scope" OR "action" as acceptable keys.
    """
    for s in token.scopes or []:
        if not isinstance(s, dict):
            continue
        if s.get("action") == required_action or s.get("scope") == required_action:
            return
    raise HTTPException(status_code=403, detail=f"Approval invalid: missing action scope '{required_action}'")


# ----------------------------
# Routes
# ----------------------------

@router.get("/state", response_model=StateResponse)
def api_get_state() -> StateResponse:
    snap = get_state()
    return StateResponse(
        state=snap.state.value,
        reason=snap.reason,
        updated_at=snap.updated_at,
        updated_by=snap.updated_by,
    )


@router.post("/state", response_model=StateResponse)
def api_set_state(
    req: StateSetRequest,
    request: Request,
    x_red_dev_key: Optional[str] = Header(default=None, alias="X-Red-Dev-Key"),
) -> StateResponse:
    # DEV-only manual set (local only)
    _dev_mode_ok(request, x_red_dev_key)

    snap = set_state(req.state, reason=req.reason, actor=req.actor, trace_id=req.trace_id)
    if snap.reason.startswith("DENIED transition"):
        raise HTTPException(status_code=403, detail=snap.reason)

    return StateResponse(
        state=snap.state.value,
        reason=snap.reason,
        updated_at=snap.updated_at,
        updated_by=snap.updated_by,
    )


@router.post("/state/arm", response_model=StateResponse)
def api_arm(reason: str = "manual arm", actor: str = "user") -> StateResponse:
    snap = arm(reason=reason, actor=actor)
    return StateResponse(state=snap.state.value, reason=snap.reason, updated_at=snap.updated_at, updated_by=snap.updated_by)


@router.post("/state/disarm", response_model=StateResponse)
def api_disarm(reason: str = "manual disarm", actor: str = "user") -> StateResponse:
    snap = disarm(reason=reason, actor=actor)
    return StateResponse(state=snap.state.value, reason=snap.reason, updated_at=snap.updated_at, updated_by=snap.updated_by)


@router.post("/state/freeze", response_model=StateResponse)
def api_freeze(reason: str = "manual freeze", actor: str = "user") -> StateResponse:
    snap = freeze(reason=reason, actor=actor)
    return StateResponse(state=snap.state.value, reason=snap.reason, updated_at=snap.updated_at, updated_by=snap.updated_by)


# Phase-7: approval-gated transitions to/from ARMED_ACTIVE

@router.post("/state/activate", response_model=StateResponse)
def api_activate(req: ActivateReq) -> StateResponse:
    _require_token_fresh(req.approval_token)
    _require_action_scope(req.approval_token, "state:activate")

    snap = set_state(WorldState.ARMED_ACTIVE, reason=req.reason, actor=req.actor, trace_id=req.trace_id)
    if snap.reason.startswith("DENIED transition"):
        raise HTTPException(status_code=403, detail=snap.reason)

    return StateResponse(
        state=snap.state.value,
        reason=snap.reason,
        updated_at=snap.updated_at,
        updated_by=snap.updated_by,
    )


@router.post("/state/deactivate", response_model=StateResponse)
def api_deactivate(req: DeactivateReq) -> StateResponse:
    _require_token_fresh(req.approval_token)
    _require_action_scope(req.approval_token, "state:deactivate")

    snap = set_state(WorldState.ARMED_IDLE, reason=req.reason, actor=req.actor, trace_id=req.trace_id)
    if snap.reason.startswith("DENIED transition"):
        raise HTTPException(status_code=403, detail=snap.reason)

    return StateResponse(
        state=snap.state.value,
        reason=snap.reason,
        updated_at=snap.updated_at,
        updated_by=snap.updated_by,
    )
