from __future__ import annotations

import time
from typing import List

from app.governance.assumptions import Assumption, AssumptionStatus
from app.world.drift import DriftEvent


class AssumptionVerifier:
    """
    Updates assumption status based on world drift.
    """
    def verify(
        self,
        *,
        assumptions: List[Assumption],
        drift_events: List[DriftEvent],
    ) -> List[Assumption]:
        drift_map = {d.key: d for d in drift_events}
        now = int(time.time() * 1000)

        for a in assumptions:
            a.last_checked_ms = now
            d = drift_map.get(a.key)
            if d:
                a.status = AssumptionStatus.VIOLATED
            else:
                a.status = AssumptionStatus.VALID

        return assumptions
