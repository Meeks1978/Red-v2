from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.container import ServiceContainer


def _safe_json_loads(b: bytes) -> Optional[Dict[str, Any]]:
    try:
        if not b:
            return None
        v = json.loads(b.decode("utf-8"))
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def _extract_trace_id(req_json: Optional[Dict[str, Any]]) -> str:
    if not isinstance(req_json, dict):
        return ""
    t = req_json.get("trace_id")
    return str(t) if t else ""


def _extract_ok(resp_json: Optional[Dict[str, Any]]) -> Optional[bool]:
    if not isinstance(resp_json, dict):
        return None
    if isinstance(resp_json.get("ok"), bool):
        return bool(resp_json["ok"])
    receipt = resp_json.get("receipt")
    if isinstance(receipt, dict) and isinstance(receipt.get("ok"), bool):
        return bool(receipt["ok"])
    result = resp_json.get("result")
    if isinstance(result, dict) and isinstance(result.get("ok"), bool):
        return bool(result["ok"])
    return None


def _extract_detail(resp_json: Optional[Dict[str, Any]]) -> str:
    if not isinstance(resp_json, dict):
        return ""
    d = resp_json.get("detail")
    return str(d) if d is not None else ""


def _semantic_key(req_json: Optional[Dict[str, Any]]) -> str:
    if not isinstance(req_json, dict):
        return "action:unknown"
    macro = req_json.get("macro", {}) or {}
    steps = macro.get("steps", []) or []
    if not steps or not isinstance(steps, list):
        return "action:unknown"

    step = steps[0] if isinstance(steps[0], dict) else {}
    runner = str(step.get("runner_id", "unknown"))
    action = str(step.get("action", "unknown"))
    args = step.get("args", {}) if isinstance(step.get("args", {}), dict) else {}

    cmd = ""
    if isinstance(args.get("cmd"), list):
        cmd = ":".join([str(x) for x in args["cmd"]])

    return f"action:{runner}:{action}:{cmd}"


class MemoryIngestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        is_execute = request.url.path.startswith("/v1/execute") and request.method.upper() == "POST"

        req_body = b""
        req_json: Optional[Dict[str, Any]] = None

        if is_execute:
            req_body = await request.body()
            req_json = _safe_json_loads(req_body)

            async def receive():
                return {"type": "http.request", "body": req_body, "more_body": False}

            request = Request(request.scope, receive)

        t0 = time.monotonic()
        response = await call_next(request)
        latency_ms = int((time.monotonic() - t0) * 1000)

        if not is_execute:
            return response

        resp_body = b""
        async for chunk in response.body_iterator:
            resp_body += chunk
        resp_json = _safe_json_loads(resp_body)

        trace_id = _extract_trace_id(req_json)
        ok = _extract_ok(resp_json)
        detail = _extract_detail(resp_json)

        # Confidence heuristic
        if ok is True:
            conf = 0.75
        elif ok is False:
            conf = 0.40
        else:
            conf = 0.50

        key = _semantic_key(req_json)

        # Stable value for equivalence
        value = {
            "status_code": response.status_code,
            "ok": ok,
            "action_key": key,
        }

        # --- Canonical (truth) ingest ---
        try:
            ServiceContainer.memory_curator.ingest(
                namespace="execute",
                key=key,
                value=value,
                source_kind="receipt",
                source_ref=trace_id or "v1_execute",
                confidence=conf,
                tags=["execute", "semantic", "receipt"],
                tier="working",
            )
        except Exception as e:
            # never break pipeline
            print({"memory_ingest_error": str(e)})

        # --- Semantic (recall) upsert with breaker + budget ---
        try:
            sem = getattr(ServiceContainer, "semantic_memory", None)
            enabled_sem = os.getenv("ENABLE_SEMANTIC_MEMORY", "").lower() == "true"
            budget_ms = int(os.getenv("SEMANTIC_BUDGET_MS", "50"))

            if not enabled_sem or sem is None:
                # semantic disabled
                return Response(
                    content=resp_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            breaker = getattr(ServiceContainer, "semantic_breaker", None)
            rt = ServiceContainer.runtime

            if breaker is not None and not breaker.allow():
                rt["semantic_upsert_skip"] += 1
                return Response(
                    content=resp_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            su0 = time.monotonic()
            text = f"{key} status={response.status_code} ok={ok} detail={detail}"
            sem.upsert(
                point_id=key,
                text=text,
                payload={
                    "namespace": "execute",
                    "key": key,
                    "status_code": response.status_code,
                    "ok": ok,
                    "trace_id": trace_id or None,
                    "latency_ms": latency_ms,
                },
            )
            su_ms = int((time.monotonic() - su0) * 1000)

            rt["semantic_last_upsert_ms"] = su_ms
            rt["semantic_last_error"] = None

            if su_ms > budget_ms:
                rt["semantic_upsert_budget_exceeded"] += 1
                if breaker is not None:
                    breaker.record_failure(f"budget_exceeded {su_ms}ms>{budget_ms}ms")
            else:
                rt["semantic_upsert_ok"] += 1
                if breaker is not None:
                    breaker.record_success()

        except Exception as e:
            rt = ServiceContainer.runtime
            rt["semantic_upsert_fail"] += 1
            rt["semantic_last_error"] = str(e)[:300]
            br = getattr(ServiceContainer, "semantic_breaker", None)
            if br is not None:
                br.record_failure(str(e))
            # never raise
            print({"semantic_upsert_error": str(e)})

        return Response(
            content=resp_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
