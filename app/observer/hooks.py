from __future__ import annotations

from typing import List

from app.world.drift import DriftEvent
from app.governance.uncertainty_gate import GateDecision
from app.trust.surface import ReasonSurface
from app.services.container import ServiceContainer


def observer_snapshot(
    *,
    drift_events: List[DriftEvent],
    gate_decisions: List[GateDecision],
    trust_surfaces: List[ReasonSurface],
    override_events: int = 0,
) -> None:
    """
    Safe, explicit call-in.
    No scheduling. No side-effects beyond metrics/logs.
    """
    ServiceContainer.shadow_observer.tick_heartbeat(
        drift_events=drift_events,
        gate_decisions=gate_decisions,
        trust_surfaces=trust_surfaces,
        override_events=override_events,
    )
