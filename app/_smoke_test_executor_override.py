from __future__ import annotations

from app.services.container import ServiceContainer
from app.types.core import Confidence, new_id
from app.governance.uncertainty_gate import GateDecision
import time


def safe_action():
    print("✅ EXECUTED UNDER OVERRIDE")
    return {"status": "executed"}


def main() -> None:
    c = ServiceContainer()

    gate = GateDecision(
        allowed=False,
        reason="forced test",
        confidence=Confidence(0.2, "forced"),
    )

    result = c.executor.execute(
        action=safe_action,
        gate_decision=gate,
        trace_id=new_id("trace"),
        absolute_override=True,
    )

    print("EXECUTED:", result.executed)
    print("RECEIPT OK:", result.receipt.ok)


if __name__ == "__main__":
    main()
