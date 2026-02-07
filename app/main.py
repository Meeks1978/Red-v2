from fastapi import FastAPI

app = FastAPI(title="Red v2 (Copilot)", version="0.1.0")

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
