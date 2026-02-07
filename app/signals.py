from __future__ import annotations

import os
import httpx

def control_plane_url() -> str:
    return os.getenv("CONTROL_PLANE_URL", "").rstrip("/")

def probe_control_plane(timeout_sec: float = 1.5) -> tuple[bool, str]:
    """
    Read-only probe. Never raises. Never POSTs.
    Returns (ok, detail).
    """
    url = control_plane_url()
    if not url:
        return False, "CONTROL_PLANE_URL not set"

    try:
        with httpx.Client(timeout=timeout_sec) as client:
            r = client.get(f"{url}/health", headers={"Accept": "application/json"})
        if 200 <= r.status_code < 300:
            return True, f"reachable: {url}/health ({r.status_code})"
        return False, f"unhealthy: {url}/health ({r.status_code})"
    except Exception as e:
        return False, f"unreachable: {url}/health ({e})"
