from fastapi import FastAPI

# ---- Routers ----
from app.state_api import router as state_router
from app.approvals_api import router as approvals_router
from app.execute_api import router as execute_router

# Optional routers (include only if they exist in your repo)
try:
    from app.pillars_api import router as pillars_router
except Exception:
    pillars_router = None

try:
    from app.world_entities_api import router as world_entities_router
except Exception:
    world_entities_router = None

try:
    from app.world_events_api import router as world_events_router
except Exception:
    world_events_router = None

try:
    from app.world_entities_api import router as world_entities_router
except Exception:
    world_entities_router = None


# ---- App ----
app = FastAPI(
    title="Red v2",
    version="2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---- Core Routers ----
app.include_router(state_router)
app.include_router(approvals_router)
app.include_router(execute_router)

# ---- Optional Routers ----
if pillars_router:
    app.include_router(pillars_router)

if world_entities_router:
    app.include_router(world_entities_router)

if world_events_router:
    app.include_router(world_events_router)


# ---- Health ----
@app.get("/health")
def health():
    return {"ok": True, "service": "red-v2"}