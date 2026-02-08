from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

RED_BASE_URL = os.getenv("RED_BASE_URL", "http://red:8111").rstrip("/")
TIMEOUT_S = float(os.getenv("COPILOT_TIMEOUT_S", "30"))

app = FastAPI(title="Red Copilot Client", version="2.0.0")


class ApprovalRequest(BaseModel):
    # Pass-through payload. Your spine decides structure.
    payload: Dict[str, Any] = Field(default_factory=dict)


class ExecuteRequest(BaseModel):
    macro: Dict[str, Any]
    approval_token: str
    plan_id: Optional[str] = None
    trace_id: Optional[str] = None


@app.get("/health")
def health():
    return {"ok": True, "service": "red-copilot-client", "red_base_url": RED_BASE_URL}


@app.get("/red/health")
def red_health():
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            r = client.get(f"{RED_BASE_URL}/health")
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"cannot reach red: {e}") from e


@app.get("/state")
def get_state():
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            r = client.get(f"{RED_BASE_URL}/v1/state")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"red state failed: {e}") from e


@app.post("/arm")
def arm(reason: str = "copilot arm", actor: str = "copilot"):
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            r = client.post(f"{RED_BASE_URL}/v1/state/arm", params={"reason": reason, "actor": actor})
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"red arm failed: {e}") from e


@app.post("/disarm")
def disarm(reason: str = "copilot disarm", actor: str = "copilot"):
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            r = client.post(f"{RED_BASE_URL}/v1/state/disarm", params={"reason": reason, "actor": actor})
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"red disarm failed: {e}") from e


@app.post("/approval/request")
def approval_request(req: ApprovalRequest):
    """
    Client-only: forwards to Red spine approval request endpoint.
    """
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            r = client.post(f"{RED_BASE_URL}/approval/request", json=req.payload)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"approval request failed: {e}") from e


@app.post("/execute")
def execute(req: ExecuteRequest):
    """
    Client-only: forwards to Red spine execute endpoint.
    """
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            r = client.post(f"{RED_BASE_URL}/v1/execute", json=req.model_dump())
        # propagate Red's status codes (403/401/etc) for transparency
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"execute forward failed: {e}") from e

@app.post("/approval/verify")
def approval_verify(payload: Dict[str, Any]):
    """
    Client-only: forwards approval verification to Red spine.
    """
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            r = client.post(f"{RED_BASE_URL}/approval/verify", json=payload)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"approval verify failed: {e}") from e


@app.post("/approval/consume")
def approval_consume(payload: Dict[str, Any]):
    """
    Client-only: forwards approval consumption to Red spine.
    """
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            r = client.post(f"{RED_BASE_URL}/approval/consume", json=payload)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"approval consume failed: {e}") from e
