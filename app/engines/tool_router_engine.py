from __future__ import annotations
from typing import Any, Dict

from app.contracts.execution import BoundStep

class ToolRouterEngine:
    def bind(self, step: Dict[str, Any], ctx: Dict[str, Any]) -> BoundStep:
        # minimal binder: expects runner_id/action/args provided
        return BoundStep(
            runner_id=str(step.get("runner_id","unknown")),
            action=str(step.get("action","unknown")),
            args=dict(step.get("args") or {}),
        )
