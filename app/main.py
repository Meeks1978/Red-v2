from __future__ import annotations

from fastapi import FastAPI
from red.app.routers.meta import router as meta_router

app = FastAPI()
app.include_router(meta_router)

from app import approvals_api
from app import state_api
from app import execute_api
from app import pillars_api

from app import world_events_api
from app import world_events_sse
from app import world_entities_api
from app import world_probes_api

from app import world_replay_api
from app import receipts_explain_api

app = FastAPI(title="Red v2", version="2.0.0")

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

@app.get("/health")
def health():
    return {"ok": True, "service": "red-v2"}
