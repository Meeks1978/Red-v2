from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from red.app.world.types import WorldFact


@dataclass(frozen=True)
class DriftEvent:
    key: str
    expected: Any
    observed: Any
    confidence_drop: float
    reason: str


class WorldDriftDetector:
    """
    Compare expected vs observed world facts.
    """
    def detect(
        self,
        *,
        expected: Dict[str, Any],
        facts: List[WorldFact],
    ) -> List[DriftEvent]:
        drift: List[DriftEvent] = []
        fact_map = {f.key: f for f in facts}

        for key, expected_value in expected.items():
            f = fact_map.get(key)
            if not f:
                drift.append(
                    DriftEvent(
                        key=key,
                        expected=expected_value,
                        observed=None,
                        confidence_drop=0.4,
                        reason="expected fact missing",
                    )
                )
                continue

            if f.value != expected_value:
                drift.append(
                    DriftEvent(
                        key=key,
                        expected=expected_value,
                        observed=f.value,
                        confidence_drop=0.5,
                        reason="observed value differs",
                    )
                )

        return drift
