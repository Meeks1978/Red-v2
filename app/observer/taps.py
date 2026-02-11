from __future__ import annotations

from typing import List, Optional

from app.observer.hooks import observer_snapshot
from app.world.drift import DriftEvent
from app.governance.uncertainty_gate import GateDecision
from app.trust.surface import ReasonSurface


def tap_execute(
    *,
    drift_events: Optional[List[DriftEvent]] = None,
    gate_decision: Optional[GateDecision] = None,
    trust_surface: Optional[ReasonSurface] = None,
    absolute_override_used: bool = False,
) -> None:
    """
    Safe Phase-0 telemetry tap for /execute.
    - Never raises (won't break execute)
    - No side effects beyond shadow metrics/log line
    """
    try:
        observer_snapshot(
            drift_events=drift_events or [],
            gate_decisions=[gate_decision] if gate_decision else [],
            trust_surfaces=[trust_surface] if trust_surface else [],
            override_events=1 if absolute_override_used else 0,
        )
    except Exception as e:
        # Never break /execute for observer issues
        print({"observer": "shadow", "tap": "execute", "error": str(e)})
