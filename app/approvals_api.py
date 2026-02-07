from fastapi import APIRouter, HTTPException
from app.approval_schema import (
    ApprovalRequest,
    ApprovalToken,
    ApprovalVerifyRequest,
    ApprovalVerifyResponse,
    ApprovalConsumeRequest,
    ApprovalConsumeResponse,
)
from app.approvals import request_approval, verify_approval, consume_approval, store_stats

router = APIRouter()

@router.post("/approval/request", response_model=ApprovalToken)
def approval_request(req: ApprovalRequest):
    try:
        return request_approval(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approval/verify", response_model=ApprovalVerifyResponse)
def approval_verify(req: ApprovalVerifyRequest):
    return verify_approval(req)

@router.post("/approval/consume", response_model=ApprovalConsumeResponse)
def approval_consume(req: ApprovalConsumeRequest):
    return consume_approval(req)

@router.get("/approval/stats")
def approval_stats():
    return store_stats()
