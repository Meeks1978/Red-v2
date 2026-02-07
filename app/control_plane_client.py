from __future__ import annotations

import os
import httpx
from typing import Any, Dict, Optional, Tuple


DEFAULT_TIMEOUT = 3.0

def control_plane_url() -> str:
    return os.getenv("CONTROL_PLANE_URL", "http://control-plane-meeks-control-plane:8088").rstrip("/")


def _get(path: str) -> Tuple[int, Any]:
    """
    Read-only GET helper with short timeouts.
    Returns (status_code, json_or_text).
    """
    url = f"{control_plane_url()}{path}"
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            r = client.get(url, headers={"Accept": "application/json"})
        ct = (r.headers.get("content-type") or "").lower()
        if "application/json" in ct:
            return r.status_code, r.json()
        return r.status_code, r.text
    except Exception as e:
        return 0, {"error": str(e), "url": url}


def probe_health() -> Dict[str, Any]:
    """
    Try common health endpoints; return the first successful response.
    """
    candidates = ["/health", "/healthz", "/status", "/"]
    for p in candidates:
        code, payload = _get(p)
        if code and 200 <= code < 300:
            return {"ok": True, "endpoint": p, "status_code": code, "payload": payload}
    return {"ok": False, "endpoint": None, "status_code": 0, "payload": {"error": "no healthy endpoint found"}}


def fetch_info() -> Dict[str, Any]:
    """
    Try to fetch an info-like payload (optional).
    """
    candidates = ["/info", "/version", "/about"]
    for p in candidates:
        code, payload = _get(p)
        if code and 200 <= code < 300:
            return {"ok": True, "endpoint": p, "status_code": code, "payload": payload}
    return {"ok": False, "endpoint": None, "status_code": 0, "payload": {"error": "no info endpoint found"}}


def list_runners() -> Dict[str, Any]:
    """
    Optional: only works if your control plane exposes it.
    """
    candidates = ["/runners", "/v1/runners", "/api/runners"]
    for p in candidates:
        code, payload = _get(p)
        if code and 200 <= code < 300:
            return {"ok": True, "endpoint": p, "status_code": code, "payload": payload}
    return {"ok": False, "endpoint": None, "status_code": 0, "payload": {"error": "no runners endpoint found"}}
