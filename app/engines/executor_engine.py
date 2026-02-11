from __future__ import annotations
from typing import Any, Dict

from app.contracts.execution import ExecutionPlan, ExecutionResult

class ExecutorEngine:
    """
    Scaffold. Real execution stays in your existing /v1/execute path.
    This engine remains OFF by default until you wire it.
    """
    enabled: bool = False

    def execute(self, plan: ExecutionPlan, ctx: Dict[str, Any]) -> ExecutionResult:
        return ExecutionResult(ok=False, error="ExecutorEngine scaffold: not wired.")

# --- Compatibility alias (scaffold wiring expects this name) ---
GuardedExecutor = ExecutorEngine
