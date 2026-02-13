from __future__ import annotations

from app.services.container import ServiceContainer
from app.governance.assumptions import Assumption
from app.types.core import Confidence
from app.world.types import WorldFact, Source, new_id
import time


def main() -> None:
    c = ServiceContainer()

    # World fact contradicts assumption
    src = Source(source_id=new_id("src"), kind="sensor", trust=0.9)
    fact = WorldFact(
        fact_id=new_id("fact"),
        key="user_available",
        value=True,
        observed_at_ms=int(time.time() * 1000),
        source=src,
        ttl_ms=10000,
    )
    c.world_engine.observe(fact)

    analysis = c.world_engine.analyze(
        expected={"user_available": False}
    )

    assumptions = [
        Assumption(
            key="user_available",
            expected_value=False,
            description="User must be unavailable before sending email",
        )
    ]

    decision = c.advisory_engine.apply_uncertainty_governance(
        assumptions=assumptions,
        drift_events=analysis["drift"],
        confidence=Confidence(0.85, "initial confidence"),
    )

    print("ALLOWED:", decision.allowed)
    print("REASON:", decision.reason)
    print("CONF:", decision.confidence.score, "-", decision.confidence.rationale)


if __name__ == "__main__":
    main()
