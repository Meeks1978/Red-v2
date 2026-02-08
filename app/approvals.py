from __future__ import annotations

import os
import hmac
import hashlib
import base64
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from app.approval_schema import (
    ApprovalRequest,
    ApprovalToken,
    ApprovalVerifyRequest,
    ApprovalVerifyResponse,
    ApprovalConsumeRequest,
    ApprovalConsumeResponse,
)

# In-memory approval store (Phase-1)
_STORE: Dict[str, ApprovalToken] = {}


# ---------- helpers ----------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _secret() -> bytes:
    s = os.getenv("APPROVAL_SIGNING_SECRET", "")
    if len(s) < 16:
        raise RuntimeError("APPROVAL_SIGNING_SECRET must be set (>=16 chars).")
    return s.encode("utf-8")


def _ttl_seconds() -> int:
    try:
        return int(os.getenv("APPROVAL_TOKEN_TTL_SEC", "300"))
    except Exception:
        return 300


# ---------- canonical signing ----------

def _canonical_payload(token: ApprovalToken) -> bytes:
    """
    Canonical bytes for signing.
    This MUST be deterministic and MUST exclude signature/status.
    """
    parts: List[str] = []

    parts.append(f"token_id={token.token_id}")
    parts.append(f"nonce={token.nonce}")
    parts.append(f"issued_at={token.issued_at}")
    parts.append(f"expires_at={token.expires_at}")
    parts.append(f"proposal_id={token.proposal_id}")

    for i, scope in enumerate(token.scopes):
        parts.append(f"scope[{i}].runner_id={scope.runner_id}")
        parts.append(f"scope[{i}].action={scope.action}")
        for k in sorted(scope.args.keys()):
            parts.append(f"scope[{i}].args.{k}={repr(scope.args[k])}")
        parts.append(f"scope[{i}].risk={scope.risk}")

    canonical = "\n".join(parts)
    return canonical.encode("utf-8")


def _sign(token: ApprovalToken) -> str:
    mac = hmac.new(_secret(), _canonical_payload(token), hashlib.sha256).digest()
    return _b64url(mac)


def _is_expired(token: ApprovalToken) -> bool:
    try:
        exp = datetime.fromisoformat(token.expires_at.replace("Z", "+00:00"))
    except Exception:
        return True
    return _now() >= exp


# ---------- API operations ----------

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

    stored = _STORE.get(token.token_id)
    if stored is None:
        return ApprovalVerifyResponse(ok=False, status="INVALID", reason="Unknown token_id")

    # 🔐 AUTHORITATIVE signature check (stored token only)
    try:
        expected_sig = _sign(stored)
    except Exception as e:
        return ApprovalVerifyResponse(ok=False, status="INVALID", reason=str(e))

    if not hmac.compare_digest(expected_sig, token.signature):
        return ApprovalVerifyResponse(ok=False, status="INVALID", reason="Signature mismatch")

    # Field integrity check
    if (
        token.nonce != stored.nonce
        or token.issued_at != stored.issued_at
        or token.expires_at != stored.expires_at
    ):
        return ApprovalVerifyResponse(ok=False, status="INVALID", reason="Token fields do not match issued record")

    if _is_expired(stored):
        stored.status = "EXPIRED"
        return ApprovalVerifyResponse(ok=False, status="EXPIRED", reason="Token expired", expires_at=stored.expires_at)

    if stored.status != "PENDING":
        return ApprovalVerifyResponse(ok=False, status=stored.status, reason=f"Token not pending: {stored.status}")

    return ApprovalVerifyResponse(ok=True, status="PENDING", reason="Token valid", expires_at=stored.expires_at)


def consume_approval(creq: ApprovalConsumeRequest) -> ApprovalConsumeResponse:
    stored = _STORE.get(creq.token_id)
    if stored is None:
        return ApprovalConsumeResponse(ok=False, status="NOT_FOUND", reason="Unknown token_id")

    if stored.nonce != creq.nonce:
        return ApprovalConsumeResponse(ok=False, status="REVOKED", reason="Nonce mismatch")

    if _is_expired(stored):
        stored.status = "EXPIRED"
        return ApprovalConsumeResponse(ok=False, status="EXPIRED", reason="Token expired")

    if stored.status != "PENDING":
        return ApprovalConsumeResponse(ok=False, status=stored.status, reason=f"Token not pending: {stored.status}")

    stored.status = "CONSUMED"
    return ApprovalConsumeResponse(ok=True, status="CONSUMED", reason="Token consumed (single-use)")


def store_stats() -> Dict[str, Any]:
    by_status: Dict[str, int] = {}
    for t in _STORE.values():
        by_status[t.status] = by_status.get(t.status, 0) + 1
    return {"total": len(_STORE), "by_status": by_status}
