from __future__ import annotations

import os
import hmac
import hashlib
import base64
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from app.approval_schema import (
    ApprovalRequest,
    ApprovalToken,
    ApprovalVerifyRequest,
    ApprovalVerifyResponse,
    ApprovalConsumeRequest,
    ApprovalConsumeResponse,
    ActionScope,
)

# NOTE: Phase-1: in-memory store (container-local). This is fine for now.
# Later: persist to Qdrant/Postgres or an approvals service (shortcuts-gateway).
_STORE: Dict[str, ApprovalToken] = {}

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _secret() -> bytes:
    s = os.getenv("APPROVAL_SIGNING_SECRET", "")
    if len(s) < 16:
        # Fail-closed: approvals should not be used without a real secret.
        # Still allows /propose and /health to function.
        raise RuntimeError("APPROVAL_SIGNING_SECRET must be set (>=16 chars).")
    return s.encode("utf-8")

def _ttl_seconds() -> int:
    try:
        return int(os.getenv("APPROVAL_TOKEN_TTL_SEC", "300"))
    except Exception:
        return 300

def _canonical_payload(token: ApprovalToken) -> bytes:
    """
    Create canonical bytes for signing.
    We sign fields that must not be tampered with:
    token_id, nonce, issued_at, expires_at, proposal_id, scopes.
    """
    # Deterministic JSON-ish canonical form without importing json canonicalization libs.
    # Keep it simple but stable:
    parts: List[str] = []
    parts.append(f"token_id={token.token_id}")
    parts.append(f"nonce={token.nonce}")
    parts.append(f"issued_at={token.issued_at}")
    parts.append(f"expires_at={token.expires_at}")
    parts.append(f"proposal_id={token.proposal_id}")

    for i, s in enumerate(token.scopes):
        parts.append(f"scope[{i}].runner_id={s.runner_id}")
        parts.append(f"scope[{i}].action={s.action}")
        # args: stable ordering by key
        for k in sorted(s.args.keys()):
            parts.append(f"scope[{i}].args.{k}={repr(s.args[k])}")
        parts.append(f"scope[{i}].risk={s.risk}")

    return ("\n".join(parts)).encode("utf-8")

def _sign(token: ApprovalToken) -> str:
    mac = hmac.new(_secret(), _canonical_payload(token), hashlib.sha256).digest()
    return _b64url(mac)

def _is_expired(token: ApprovalToken) -> bool:
    try:
        exp = datetime.fromisoformat(token.expires_at.replace("Z", "+00:00"))
    except Exception:
        return True
    return _now() >= exp

def request_approval(req: ApprovalRequest) -> ApprovalToken:
    issued = _now()
    exp = issued + timedelta(seconds=_ttl_seconds())

    token = ApprovalToken(
        token_id=str(uuid4()),
        issued_at=issued.isoformat(),
        expires_at=exp.isoformat(),
        nonce=_b64url(os.urandom(18)),
        proposal_id=req.proposal_id,
        scopes=req.scopes,
        signature="",
        status="PENDING",
    )

    token.signature = _sign(token)
    _STORE[token.token_id] = token
    return token

def verify_approval(vreq: ApprovalVerifyRequest) -> ApprovalVerifyResponse:
    token = vreq.token

    # 1) Existence check (must match stored token id)
    stored = _STORE.get(token.token_id)
    if stored is None:
        return ApprovalVerifyResponse(ok=False, status="INVALID", reason="Unknown token_id")

    # 2) Signature check against stored canonical form
    # Use the incoming token fields to verify integrity, but also ensure it matches stored.
    try:
        expected_sig = _sign(token)
    except Exception as e:
        return ApprovalVerifyResponse(ok=False, status="INVALID", reason=str(e))

    if not hmac.compare_digest(expected_sig, token.signature):
        return ApprovalVerifyResponse(ok=False, status="INVALID", reason="Signature mismatch")

    # 3) Stored equality checks (prevent swapping fields while keeping signature)
    # Ensure token fields match what we issued.
    if token.nonce != stored.nonce or token.expires_at != stored.expires_at or token.issued_at != stored.issued_at:
        return ApprovalVerifyResponse(ok=False, status="INVALID", reason="Token fields do not match issued record")

    if token.status != stored.status:
        # client may have stale status; we trust store
        token_status = stored.status
    else:
        token_status = stored.status

    # 4) Status / expiry checks
    if _is_expired(stored):
        stored.status = "EXPIRED"
        _STORE[stored.token_id] = stored
        return ApprovalVerifyResponse(ok=False, status="EXPIRED", reason="Token expired", expires_at=stored.expires_at)

    if stored.status != "PENDING":
        return ApprovalVerifyResponse(ok=False, status=stored.status, reason=f"Token not pending: {stored.status}", expires_at=stored.expires_at)

    # 5) Optional scope match check
    if vreq.expected_scope is not None:
        ok = any(
            (s.runner_id == vreq.expected_scope.runner_id and
             s.action == vreq.expected_scope.action and
             s.args == vreq.expected_scope.args)
            for s in stored.scopes
        )
        if not ok:
            return ApprovalVerifyResponse(ok=False, status="INVALID", reason="Token does not cover expected scope", expires_at=stored.expires_at)

    return ApprovalVerifyResponse(ok=True, status="PENDING", reason="Token valid and pending", expires_at=stored.expires_at)

def consume_approval(creq: ApprovalConsumeRequest) -> ApprovalConsumeResponse:
    stored = _STORE.get(creq.token_id)
    if stored is None:
        return ApprovalConsumeResponse(ok=False, status="NOT_FOUND", reason="Unknown token_id")

    if stored.nonce != creq.nonce:
        return ApprovalConsumeResponse(ok=False, status="REVOKED", reason="Nonce mismatch (treat as invalid/revoked)")

    if _is_expired(stored):
        stored.status = "EXPIRED"
        _STORE[stored.token_id] = stored
        return ApprovalConsumeResponse(ok=False, status="EXPIRED", reason="Token expired")

    if stored.status != "PENDING":
        return ApprovalConsumeResponse(ok=False, status=stored.status, reason=f"Token not pending: {stored.status}")

    stored.status = "CONSUMED"
    _STORE[stored.token_id] = stored
    return ApprovalConsumeResponse(ok=True, status="CONSUMED", reason="Token consumed (single-use)")

def store_stats() -> Dict[str, Any]:
    total = len(_STORE)
    by_status: Dict[str, int] = {}
    for t in _STORE.values():
        by_status[t.status] = by_status.get(t.status, 0) + 1
    return {"total": total, "by_status": by_status}
