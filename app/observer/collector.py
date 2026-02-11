from __future__ import annotations

from typing import Dict, List

from app.services.container import ServiceContainer
from app.observer.hooks import observer_snapshot
from app.world.drift import DriftEvent
from app.governance.uncertainty_gate import GateDecision
from app.trust.surface import ReasonSurface
from app.types.core import Confidence


class ShadowCollector:
    """
    Collects read-only signals for the shadow observer.
    Phase-0 conservative default: no 'expected' model, so drift is empty unless provided.
    """

    def __init__(self) -> None:
        self.expected: Dict[str, object] = {}  # can be set later (still read-only)

    def tick(self) -> None:
        # World analysis (read-only)
        analysis = ServiceContainer.world_engine.analyze(expected=self.expected)

        drift_events: List[DriftEvent] = analysis.get("drift", [])
        # No gate decisions by default; caller can wire real ones later
        gate_decisions: List[GateDecision] = []
        trust_surfaces: List[ReasonSurface] = []

        # If you want a minimal “heartbeat” trust surface, you can uncomment later,
        # but for now keep it empty to avoid noise.

        observer_snapshot(
            drift_events=drift_events,
            gate_decisions=gate_decisions,
            trust_surfaces=trust_surfaces,
            override_events=0,
        )
