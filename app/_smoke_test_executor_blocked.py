from __future__ import annotations

from app.services.container import ServiceContainer
from app.types.core import Confidence, new_id
from app.governance.assumptions import Assumption
from app.world.types import WorldFact, Source
import time


def dangerous_action():
    print("🔥 THIS SHOULD NOT RUN")
    return {"status": "executed"}


def main() -> None:
    c = ServiceContainer()

    # World contradicts assumption
    src = Source(source_id=new_id("src"), kind="sensor", trust=0.9)
    fact = WorldFact(
        fact_id=new_id("fact"),
        key="system_safe",
        value=False,
        observed_at_ms=int(time.time() * 1000),
        source=src,
    )
    c.world_engine.observe(fact)

    analysis = c.world_engine.analyze(
        expected={"system_safe": True}
    )

    assumptions = [
        Assumption(
            key="system_safe",
            expected_value=True,
            description="System must be safe",
        )
    ]

    gate = c.advisory_engine.apply_uncertainty_governance(
        assumptions=assumptions,
        drift_events=analysis["drift"],
        confidence=Confidence(0.9, "initial"),
    )

    result = c.executor.execute(
        action=dangerous_action,
        gate_decision=gate,
        trace_id=new_id("trace"),
        absolute_override=False,
    )

    print("EXECUTED:", result.executed)
    print("RECEIPT OK:", result.receipt.ok)
    print("ERROR:", result.receipt.error)


if __name__ == "__main__":
    main()
