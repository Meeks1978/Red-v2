from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from app.services.container import ServiceContainer

# DriftDetector exists in your repo (you showed it earlier)
from app.world.drift import DriftDetector


router = APIRouter(prefix="/health", tags=["health"])


def _safe_world_health() -> Dict[str, Any]:
    """
    Phase-7 rule: NEVER raise from health surfaces.
    Return best-effort structured telemetry about BU-4 world layer.
    """
    out: Dict[str, Any] = {
        "ok": False,
        "world": {
            "store": {},
            "counts": {},
            "drift": {},
        },
        "error": None,
    }

    try:
        eng = ServiceContainer.world_engine
        store = getattr(eng, "store", None)
        if store is None:
            out["error"] = "world_engine.store missing"
            return out

        # --- store path (best effort)
        db_path = getattr(store, "db_path", None)
        out["world"]["store"]["db_path"] = str(db_path) if db_path is not None else None

        # --- counts (best effort)
        for fn_name, key in [
            ("count_entities", "entities"),
            ("count_events", "events"),
            ("count_relations", "relations"),
        ]:
            fn = getattr(store, fn_name, None)
            if callable(fn):
                try:
                    out["world"]["counts"][key] = int(fn())
                except Exception:
                    # never raise from health
                    pass

        # last event ts (best effort)
        last_ts_fn = getattr(store, "last_event_ts", None)
        if callable(last_ts_fn):
            try:
                out["world"]["store"]["last_event_ts"] = last_ts_fn()
            except Exception:
                pass

        # --- drift (best effort)
        try:
            det = DriftDetector(store)
            d = det.compute(limit_entities=50)
            # expected keys: ok/fingerprint/drift_events/count (per your drift scaffolds)
            out["world"]["drift"]["ok"] = bool(d.get("ok", True))
            out["world"]["drift"]["fingerprint"] = d.get("fingerprint")
            out["world"]["drift"]["count"] = int(d.get("count", 0) or 0)
        except Exception:
            # drift health is optional; never raise
            pass

        out["ok"] = True
        return out

    except Exception as e:
        out["error"] = str(e)
        return out


@router.get("/world")
def health_world() -> Dict[str, Any]:
    return _safe_world_health()
