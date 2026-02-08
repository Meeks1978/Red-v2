from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Red v2", version="2.0.0")

def _include(path: str):
    mod = __import__(path, fromlist=["router"])
    app.include_router(mod.router)

# Core APIs
_include("app.pillars_api")
_include("app.approvals_api")
_include("app.state_api")
_include("app.execute_api")

@app.get("/health")
def health():
    return {"ok": True, "service": "red-v2"}
