from __future__ import annotations

from typing import Dict, Any, List

from app.world.store import WorldStore
from app.world.staleness import StalenessMonitor
from app.world.trust_weighting import SensorTrustWeighting
from app.world.drift import WorldDriftDetector, DriftEvent
from app.world.types import WorldFact


class WorldEngine:
    def __init__(self) -> None:
        self.store = WorldStore()
        self.staleness = StalenessMonitor()
        self.trust_weighting = SensorTrustWeighting()
        self.drift = WorldDriftDetector()

    def observe(self, fact: WorldFact) -> None:
        self.store.upsert_fact(fact)

    def analyze(self, *, expected: Dict[str, Any]) -> Dict[str, Any]:
        facts = list(self.store.all_facts())

        stale = self.staleness.find_stale(facts)
        drift = self.drift.detect(expected=expected, facts=facts)

        return {
            "facts": facts,
            "stale": stale,
            "drift": drift,
        }
