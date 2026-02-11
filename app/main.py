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


app = FastAPI(title="Red v2", version="2.0.0")

# Meta
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
    # Recompute on demand (non-strict) to reflect live state too
    live = startup_invariants(app, ServiceContainer)
    return {
        "ok": True,
        "service": "red-v2",
        "startup_invariants": _LAST_INVARIANTS,
        "live_invariants": live,
    }

# --- Runtime hardening endpoint ---
from app.services.container import ServiceContainer

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

app.include_router(advisory_router)
app.include_router(planning_router)
app.include_router(observer_engine_router)
app.include_router(world_engine_router)
app.include_router(upgrades_router)

# --- Orchestrator API ---
from app.api.orchestrator_api import router as orchestrator_router
app.include_router(orchestrator_router)
