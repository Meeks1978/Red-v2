from __future__ import annotations

from typing import Any, Dict


class SensorTrustWeights:
    """
    Placeholder for BU-4/Phase-7 sensor trust weighting.
    Keep simple: static weights by source.
    """

    def __init__(self) -> None:
        self.weights: Dict[str, float] = {
            "world": 0.8,
            "execute": 0.9,
            "manual": 0.7,
            "unknown": 0.5,
        }

    def weight(self, source: str) -> float:
        try:
            return float(self.weights.get(source or "unknown", 0.5))
        except Exception:
            return 0.5

    def report(self) -> Dict[str, Any]:
        return {"ok": True, "weights": dict(self.weights)}
