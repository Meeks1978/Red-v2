from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from red.app.types.core import Receipt, Confidence
from red.app.governance.uncertainty_gate import GateDecision
from red.app.types.core import new_id


@dataclass
class ExecutionResult:
    executed: bool
    receipt: Receipt


class GuardedExecutor:
    """
    Executes actions ONLY if governance allows.
    Does not decide — only enforces.
    """

    def execute(
        self,
        *,
        action: Callable[[], Dict[str, Any]],
        gate_decision: GateDecision,
        trace_id: str,
        step_id: Optional[str] = None,
        absolute_override: bool = False,
    ) -> ExecutionResult:

        step_id = step_id or new_id("step")
        start_ms = Receipt.now_ms()

        # Hard stop unless explicitly overridden
        if not gate_decision.allowed and not absolute_override:
            end_ms = Receipt.now_ms()
            receipt = Receipt(
                receipt_id=new_id("receipt"),
                trace_id=trace_id,
                step_id=step_id,
                ok=False,
                started_at_ms=start_ms,
                finished_at_ms=end_ms,
                output={},
                error=f"Execution blocked: {gate_decision.reason}",
            )
            return ExecutionResult(executed=False, receipt=receipt)

        # Execute action
        try:
            output = action()
            ok = True
            err = None
        except Exception as e:
            output = {}
            ok = False
            err = str(e)

        end_ms = Receipt.now_ms()
        receipt = Receipt(
            receipt_id=new_id("receipt"),
            trace_id=trace_id,
            step_id=step_id,
            ok=ok,
            started_at_ms=start_ms,
            finished_at_ms=end_ms,
            output=output,
            error=err,
        )

        return ExecutionResult(executed=ok, receipt=receipt)
