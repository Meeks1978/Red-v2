from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v.strip() if v and v.strip() else default


CONTROL_PLANE_URL = _env("CONTROL_PLANE_URL", "http://meeks-control-plane:8088").rstrip("/")


class ControlPlaneClient:
    def __init__(self, base_url: Optional[str] = None, timeout_s: float = 30.0):
        self.base_url = (base_url or CONTROL_PLANE_URL).rstrip("/")
        self.timeout_s = timeout_s

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/v1/execute", json=payload, timeout=self.timeout_s)
        # If schema fails, surface the body for debugging
        if r.status_code >= 400:
            raise RuntimeError(f"{r.status_code} {r.text}")
        return r.json()


_client = ControlPlaneClient()


def _wrap_to_macro_request(macro: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize 'macro' into the Control Plane /v1/execute schema.

    Accepts:
      - already-wrapped {runner_id, action, args}
      - {steps:[...]}  (we wrap with runner_id=ai-laptop, action=macro)
      - {macro:{steps:[...]}} (we unwrap then wrap)
      - empty {} -> still creates a valid macro with no steps (control plane may reject; better provide at least one step)
    """
    # Already looks like a control-plane request
    if "runner_id" in macro and "action" in macro:
        return macro

    # Common wrapper
    if "macro" in macro and isinstance(macro["macro"], dict):
        macro = macro["macro"]

    steps: List[Dict[str, Any]] = []
    if "steps" in macro and isinstance(macro["steps"], list):
        steps = macro["steps"]

    # Default runner_id for macro envelope (matches your schema requirements)
    runner_id = macro.get("runner_id") if isinstance(macro.get("runner_id"), str) else "ai-laptop"

    return {
        "runner_id": runner_id,
        "action": "macro",
        "args": {
            "steps": steps
        }
    }


def execute_macro(macro: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point used by execute_api.py.
    """
    payload = _wrap_to_macro_request(macro)
    return _client.execute(payload)
