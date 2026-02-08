from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.world_state import can_execute
from app.approval_schema import ApprovalToken, ApprovalConsumeRequest
from app.approvals import consume_approval
from app.control_plane_client import execute_macro
from app.receipts import record_receipt
from app.world_events import emit

router = APIRouter(prefix="/v1", tags=["execute"])


class ExecuteRequest(BaseModel):
    macro: Dict[str, Any]
    approval_token: ApprovalToken
    plan_id: Optional[str] = None
    trace_id: Optional[str] = None


@router.post("/execute")
def execute(req: ExecuteRequest):
    ok, reason = can_execute()
    if not ok:
        raise HTTPException(status_code=403, detail=reason)

    emit(
        "execution_requested",
        actor="red",
        payload={
            "proposal_id": req.approval_token.proposal_id,
            "token_id": req.approval_token.token_id,
            "macro": req.macro,
        },
        trace_id=req.trace_id,
    )

    consume = consume_approval(
        ApprovalConsumeRequest(
            token_id=req.approval_token.token_id,
            nonce=req.approval_token.nonce,
        )
    )
    if not consume.ok:
        emit(
            "execution_failed",
            actor="red",
            payload={
                "proposal_id": req.approval_token.proposal_id,
                "token_id": req.approval_token.token_id,
                "error": f"approval invalid: {consume.reason}",
            },
            trace_id=req.trace_id,
        )
        raise HTTPException(status_code=403, detail=f"Approval invalid: {consume.reason}")

    try:
        result = execute_macro(req.macro)
    except Exception as e:
        emit(
            "execution_failed",
            actor="red",
            payload={
                "proposal_id": req.approval_token.proposal_id,
                "token_id": req.approval_token.token_id,
                "error": str(e),
            },
            trace_id=req.trace_id,
        )
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}")

    emit(
        "execution_succeeded",
        actor="red",
        payload={
            "proposal_id": req.approval_token.proposal_id,
            "token_id": req.approval_token.token_id,
            "result_summary": {"ok": True},
        },
        trace_id=req.trace_id,
    )

    receipt = record_receipt(
        approval_token=req.approval_token,
        macro=req.macro,
        result=result,
    )

    emit(
        "receipt_written",
        actor="red",
        payload={
            "receipt_id": receipt.get("receipt_id"),
            "proposal_id": req.approval_token.proposal_id,
            "token_id": req.approval_token.token_id,
        },
        trace_id=req.trace_id,
    )

    return receipt
