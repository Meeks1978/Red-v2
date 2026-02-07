from fastapi import FastAPI
from app.approvals_api import router as approvals_router
from app.control_plane_api import router as cp_router
from app.pillars_api import router as pillars_router
from app.propose import router as propose_router

app = FastAPI(title="Red v2 (Copilot)", version="0.1.0")

app.include_router(propose_router)
app.include_router(pillars_router)
app.include_router(cp_router)
app.include_router(approvals_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "name": "Red",
        "mode": "COPILOT",
        "world_state": "DISARMED",
        "switches": {
            "self_upgrade": False,
            "always_on_agents": False,
            "coexistence": False,
        },
        "execution": {
            "shell": False,
            "ui_automation": False,
            "docker_control": False,
        }
    }
