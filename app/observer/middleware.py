from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional, Tuple

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


def _extract_override(req_json: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(req_json, dict):
        return False
    return bool(req_json.get("absolute_override") or req_json.get("override") or req_json.get("force"))


def _extract_detail(resp_json: Optional[Dict[str, Any]]) -> str:
    if not isinstance(resp_json, dict):
        return ""
    return str(resp_json.get("detail", ""))


def _extract_receipt_ok(resp_json: Optional[Dict[str, Any]]) -> Optional[bool]:
    if not isinstance(resp_json, dict):
        return None
    receipt = resp_json.get("receipt")
    if isinstance(receipt, dict) and isinstance(receipt.get("ok"), bool):
        return bool(receipt["ok"])
    # sometimes nested: result.receipt.ok
    result = resp_json.get("result")
    if isinstance(result, dict):
        receipt = result.get("receipt")
        if isinstance(receipt, dict) and isinstance(receipt.get("ok"), bool):
            return bool(receipt["ok"])
    return None


def _classify(resp_json: Optional[Dict[str, Any]], status_code: int) -> Tuple[bool, bool, bool]:
    """
    Returns: (is_block, is_validation_error, is_http_error)
    """
    detail = _extract_detail(resp_json).lower()
    is_block = "execution blocked" in detail
    is_validation_error = status_code == 422
    is_http_error = status_code >= 500
    return is_block, is_validation_error, is_http_error


class ShadowObserverMiddleware(BaseHTTPMiddleware):
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
        override_used = _extract_override(req_json)
        receipt_ok = _extract_receipt_ok(resp_json)
        is_block, is_validation_error, is_http_error = _classify(resp_json, response.status_code)
        detail = _extract_detail(resp_json)

        try:
            ServiceContainer.shadow_observer.record_execute_event(
                status_code=response.status_code,
                latency_ms=latency_ms,
                override_used=override_used,
                is_block=is_block,
                is_validation_error=is_validation_error,
                is_http_error=is_http_error,
                receipt_ok=receipt_ok,
                detail=detail,
            )
        except Exception as e:
            print({"observer": "shadow", "tap": "middleware_v1_execute", "error": str(e)})

        return Response(
            content=resp_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
