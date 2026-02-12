from __future__ import annotations

import os
from typing import Any, Dict, Optional

from app.world.store import WorldStore
from app.world.types import Snapshot, ProbeRequest, ProbeResponse
from app.world.staleness import StalenessMonitor
from app.world.drift import DriftDetector
from app.world.trust_weighting import SensorTrustWeights
from app.engines.world_modeler_engine import WorldModelerEngine
from app.world.types import now_ms


class WorldEngine:
    """
    BU-4: World layer facade.
    Must never raise.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.store = WorldStore(db_path=db_path)
        self.staleness = StalenessMonitor(self.store)
        self.drift = DriftDetector(self.store)
        self.trust = SensorTrustWeights()
        self.modeler = WorldModelerEngine(self.store)

    def snapshot(self) -> Dict[str, Any]:
        try:
            entity_count, relation_count, event_count, last_ts = self.store.snapshot_counts()
            stale_ids = self.store.staleness(stale_after_ms=6 * 60 * 60 * 1000)
            drift = self.drift.compute(limit_entities=50)
            snap = Snapshot(
                store_path=str(self.store.db_path),
                entity_count=entity_count,
                relation_count=relation_count,
                event_count=event_count,
                last_event_ts=last_ts,
                stale_entity_count=len(stale_ids),
                drift_events_count=int(drift.get("count", 0) or 0),
            )
            return snap.model_dump()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def analyze(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Called by observer/middleware.
        Keep safe + bounded.
        """
        try:
            # In Phase-7 this will call drift/staleness gates, etc.
            return {"drift_events": [], "gate_decisions": [], "trust_surfaces": []}
        except Exception:
            return {"drift_events": [], "gate_decisions": [], "trust_surfaces": []}

    def probe(self, req: ProbeRequest) -> Dict[str, Any]:
        try:
            if req.kind == "snapshot":
                return ProbeResponse(ok=True, kind="snapshot", data=self.snapshot()).model_dump()
            if req.kind == "staleness":
                data = self.staleness.report(stale_after_ms=req.stale_after_ms)
                return ProbeResponse(ok=True, kind="staleness", data=data).model_dump()
            if req.kind == "drift":
                data = self.drift.compute(limit_entities=req.limit)
                return ProbeResponse(ok=True, kind="drift", data=data).model_dump()
            if req.kind == "trust":
                return ProbeResponse(ok=True, kind="trust", data=self.trust.report()).model_dump()
            return {"ok": False, "error": "unknown_probe"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def emit(
        self,
        kind: str,
        entity_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        source: str = "world",
    ) -> Dict[str, Any]:
        """
        BU-4 stable write path.
        Must NEVER raise.
        """

        try:
            ts = now_ms()
            payload = payload or {}

            # Optional entity upsert
            if entity_id:
                self.store.upsert_entity(
                    entity_id=entity_id,
                    kind="generic",
                    attrs=payload,
                    ts_ms=ts,
                )

            # Append event
            event = self.store.append_event(
                kind=kind,
                entity_id=entity_id,
                payload=payload,
                trace_id=trace_id,
                source=source,
                ts_ms=ts,
            )

            return {
                "ok": True,
                "event_id": event.get("event_id"),
                "ts_ms": ts,
            }

        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

