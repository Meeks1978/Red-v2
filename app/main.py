from __future__ import annotations

import os
from fastapi import FastAPI

# Meta router (your existing app router)
from app.routers.meta import router as meta_router

# Core APIs
from app import approvals_api
from app import state_api
from app import execute_api
from app import pillars_api

# World Engine
from app import world_events_api
from app import world_events_sse
from app import world_entities_api
from app import world_probes_api

# Replay / Explain
from app import world_replay_api
from app import receipts_explain_api

# Observer (Phase 0 - silent)
from app.observer.routes import router as observer_router
from app.memory.routes import router as memory_router
from app.observer.control import start_shadow_observer
from app.observer.middleware import ShadowObserverMiddleware
from app.memory.ingest_middleware import MemoryIngestMiddleware
from app.world.snapshot_api import router as world_snapshot_router


app = FastAPI(title="Red v2", version="2.0.0")

# Meta
app.include_router(world_snapshot_router)
app.include_router(meta_router)

# Core
app.include_router(approvals_api.router)
app.include_router(state_api.router)
app.include_router(execute_api.router)
app.include_router(pillars_api.router)

# World Engine
app.include_router(world_events_api.router)
app.include_router(world_events_sse.router)
app.include_router(world_entities_api.router)
app.include_router(world_probes_api.router)

# Replay / Explain
app.include_router(world_replay_api.router)
app.include_router(receipts_explain_api.router)

# Observer endpoints
app.include_router(observer_router)
app.include_router(memory_router)

# Shadow Observer startup toggle (OFF by default)
if os.getenv("ENABLE_SHADOW_OBSERVER") == "true":
    start_shadow_observer()
    app.add_middleware(ShadowObserverMiddleware)



# BU-3 Memory ingest (OFF by default)
if os.getenv('ENABLE_BU3_INGEST') == 'true':
    app.add_middleware(MemoryIngestMiddleware)
@app.get("/health")
def health():
    return {"ok": True, "service": "red-v2"}

# --- Semantic Memory Routes ---
from app.memory.semantic_routes import router as semantic_router
app.include_router(semantic_router)

# --- Operational hardening: health/details + startup invariants ---
from app.runtime.invariants import startup_invariants
from app.services.container import ServiceContainer

_LAST_INVARIANTS = {"ok": True, "failures": [], "note": "not_run_yet"}

@app.on_event("startup")
async def _startup_invariants():
    global _LAST_INVARIANTS
    _LAST_INVARIANTS = startup_invariants(app, ServiceContainer)

@app.get("/health/details")
def health_details():
    """
    Expanded health surface. Must never raise.

    World snapshot shape may evolve; this handler must be shape-tolerant.
    """
    out = {"ok": True, "service": "red-v2"}

    # World: always return a stable object with keys:
    #   ok, store, counts, drift
    try:
        from app.services.container import ServiceContainer
        import os

        # ---- counts (canonical) ----
        counts = None
        try:
            snap = ServiceContainer.world_engine.snapshot()

            # Canonical case: dict with entities/events/relations/ok
            if isinstance(snap, dict):
                # If the engine ever returns nested counts, accept it too.
                if isinstance(snap.get("counts"), dict):
                    counts = dict(snap["counts"])
                    if "ok" not in counts:
                        counts["ok"] = bool(snap.get("ok", True))
                else:
                    # Normalize key variants
                    rel = snap.get("relations", snap.get("relationships", 0))
                    counts = {
                        "ok": bool(snap.get("ok", True)),
                        "entities": int(snap.get("entities", 0) or 0),
                        "events": int(snap.get("events", 0) or 0),
                        "relations": int(rel or 0),
                    }
            # Legacy tuple/list shapes: (ok, store, counts) or (ok, store, counts, drift)
            elif isinstance(snap, (list, tuple)):
                ok = bool(snap[0]) if len(snap) >= 1 else False
                maybe_counts = snap[2] if len(snap) >= 3 else {}
                if isinstance(maybe_counts, dict):
                    counts = dict(maybe_counts)
                    counts.setdefault("ok", ok)
                else:
                    counts = {"ok": ok}
            else:
                counts = {"ok": False, "error": f"Unexpected snapshot type: {type(snap)}"}
        except Exception as e:
            counts = {"ok": False, "error": str(e)}

        # ---- store info ----
        store = None
        try:
            eng = ServiceContainer.world_engine
            st = getattr(eng, "store", None)
            if st is not None and hasattr(st, "db_path"):
                store = {"db_path": str(getattr(st, "db_path"))}
            else:
                store = {"db_path": os.getenv("WORLD_STORE_PATH", "/red/data/world.db")}
        except Exception as e:
            store = {"error": str(e)}

        # ---- drift summary (best-effort, never raise) ----
        drift = None
        try:
            eng = ServiceContainer.world_engine
            if hasattr(eng, "analyze"):
                drift = eng.analyze()  # should already be "never raise" by BU-4 discipline
            else:
                drift = {"ok": True, "drift_events": [], "note": "no analyze() on world_engine"}
        except Exception as e:
            drift = {"ok": False, "error": str(e)}

        out["world"] = {
            "ok": bool(counts.get("ok", True)) if isinstance(counts, dict) else False,
            "store": store,
            "counts": counts,
            "drift": drift,
        }

    except Exception as e:
        out["ok"] = False
        out["world"] = {"ok": False, "error": str(e)}

    return out
@app.get("/health/runtime")
def health_runtime():
    br = getattr(ServiceContainer, "semantic_breaker", None)
    return {
        "ok": True,
        "service": "red-v2",
        "runtime": getattr(ServiceContainer, "runtime", {}),
        "semantic_breaker": (br.snapshot() if br is not None else None),
    }

# --- 9-engine scaffold APIs ---
from app.api.advisory_api import router as advisory_router
from app.api.planning_api import router as planning_router
from app.api.observer_api import router as observer_engine_router
from app.api.world_api import router as world_engine_router
from app.api.upgrades_api import router as upgrades_router
from app.api.health_world_api import router as health_world_router

app.include_router(advisory_router)
app.include_router(planning_router)
app.include_router(observer_engine_router)
app.include_router(world_engine_router)
app.include_router(upgrades_router)

# --- Orchestrator API ---
from app.api.orchestrator_api import router as orchestrator_router
app.include_router(orchestrator_router)

# --- ModelGateway status API ---
from app.api.models_api import router as models_router
app.include_router(models_router)

# --- Intent->Outcome API ---
from app.api.intent_api import router as intent_router
app.include_router(intent_router)

# --- BU-1 Copilot Router ---
from red.copilot.api import router as copilot_router
app.include_router(copilot_router)
app.include_router(health_world_router)
# --- End BU-1 Copilot Router ---

