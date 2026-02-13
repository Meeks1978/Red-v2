from __future__ import annotations

import time

from app.services.container import ServiceContainer
from app.governance.assumptions import Assumption
from app.types.core import Confidence
from app.world.types import WorldFact, Source, new_id


def main() -> None:
    c = ServiceContainer()

    # World contradicts assumption
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
            description="User must be unavailable",
        )
    ]

    gate = c.advisory_engine.apply_uncertainty_governance(
        assumptions=assumptions,
        drift_events=analysis["drift"],
        confidence=Confidence(0.85, "initial confidence"),
    )

    trust = c.advisory_engine.build_trust_surface(
        base_reason="Advisory blocked",
        base_confidence=Confidence(0.85, "initial confidence"),
        assumptions=assumptions,
        drift_events=analysis["drift"],
        gate_decision=gate,
    )

    print("REASON:", trust.reason)
    print("CONF:", trust.confidence.score, "-", trust.confidence.rationale)
    print("ASSUMPTIONS:", trust.violated_assumptions)
    print("DRIFT:", trust.drift_keys)
    print("WHAT WOULD CHANGE MY MIND:", trust.what_would_change_my_mind)


if __name__ == "__main__":
    main()
