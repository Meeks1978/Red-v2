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

# --- BU-3 Memory Ingestion Hook (execute results) ---
from app.services.container import ServiceContainer

def _ingest_execute_memory(trace_id: str, response_json: dict) -> None:
    try:
        curator = ServiceContainer.memory_curator

        status_code = response_json.get("status_code")
        ok = response_json.get("ok", False)

        confidence = 0.75 if ok else 0.4

        curator.ingest(
            namespace="execute",
            key=f"trace:{trace_id}" if trace_id else "trace:unknown",
            value={
                "status_code": status_code,
                "ok": ok,
                "summary": response_json.get("detail") or response_json.get("result")
            },
            source_kind="receipt",
            source_ref=trace_id or "unknown",
            confidence=confidence,
            tags=["execute", "receipt"],
            tier="working"
        )
    except Exception as e:
        # Silent by design (Phase-0 hygiene)
        print({"memory_ingest_error": str(e)})

