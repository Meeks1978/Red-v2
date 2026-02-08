from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.world_state import can_execute
from app.approval_schema import ApprovalToken, ApprovalConsumeRequest
from app.approvals import consume_approval
from app.control_plane_client import execute_macro
from app.receipts import record_receipt

router = APIRouter(prefix="/v1", tags=["execute"])


class ExecuteRequest(BaseModel):
    macro: Dict[str, Any]
    approval_token: ApprovalToken
    plan_id: Optional[str] = None
    trace_id: Optional[str] = None


@router.post("/execute")
def execute(req: ExecuteRequest):
    # 1) HARD WORLD-STATE GATE
    ok, reason = can_execute()
    if not ok:
        raise HTTPException(status_code=403, detail=reason)

    # 2) CONSUME APPROVAL (single-use enforcement)
    consume = consume_approval(
        ApprovalConsumeRequest(
            token_id=req.approval_token.token_id,
            nonce=req.approval_token.nonce,
        )
    )
    if not consume.ok:
        raise HTTPException(
            status_code=403,
            detail=f"Approval invalid: {consume.reason}",
        )

    # 3) EXECUTE VIA CONTROL PLANE
    try:
        result = execute_macro(req.macro)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Execution failed: {e}",
        )

    # 4) RECORD RECEIPT
    receipt = record_receipt(
        approval_token=req.approval_token,
        macro=req.macro,
        result=result,
    )

    return receipt
