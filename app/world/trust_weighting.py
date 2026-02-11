from __future__ import annotations

from app.world.types import WorldFact


class SensorTrustWeighting:
    """
    Adjust effective trust based on source kind + age.
    """
    def effective_trust(self, fact: WorldFact) -> float:
        base = fact.source.trust

        # decay trust over time (simple linear decay)
        age_sec = fact.age_ms() / 1000.0
        decay = min(age_sec / 3600.0, 0.5)  # max 50% decay over 1 hour+

        kind_bias = {
            "sensor": 0.0,
            "human": 0.1,
            "inference": -0.1,
            "memory": -0.2,
        }.get(fact.source.kind, 0.0)

        return max(0.0, min(1.0, base + kind_bias - decay))
