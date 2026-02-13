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

    def snapshot(self):
        """Return a world snapshot in a shape-tolerant way.
    
        Never raise. Never blindly unpack tuples.
        """
        try:
            snap = None
            # Prefer store snapshot/counts if present
            if hasattr(self.store, "snapshot") and callable(getattr(self.store, "snapshot")):
                snap = self.store.snapshot()
            elif hasattr(self.store, "snapshot_counts") and callable(getattr(self.store, "snapshot_counts")):
                snap = self.store.snapshot_counts()
            else:
                db_path = getattr(self.store, "db_path", None)
                snap = {
                    "ok": True,
                    "store": {"db_path": str(db_path) if db_path is not None else None},
                    "counts": {"entities": 0, "events": 0, "relations": 0},
                }
    
            # Dict shape: normalize
            if isinstance(snap, dict):
                out = dict(snap)
                out.setdefault("ok", True)
                return out
    
            # Tuple/list shapes: (ok, store, counts) or (ok, store, counts, drift)
            if isinstance(snap, (list, tuple)):
                ok = bool(snap[0]) if len(snap) >= 1 else False
                store = snap[1] if len(snap) >= 2 else None
                counts = snap[2] if len(snap) >= 3 else None
                drift = snap[3] if len(snap) >= 4 else None
                out = {"ok": ok, "store": store, "counts": counts}
                if drift is not None:
                    out["drift"] = drift
                return out
    
            return {"ok": False, "error": f"Unexpected snapshot type: {type(snap)}"}
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

