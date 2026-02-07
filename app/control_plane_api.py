from fastapi import APIRouter
from app.control_plane_client import control_plane_url, probe_health, fetch_info, list_runners
from app.control_plane_client import fetch_openapi


router = APIRouter()

@router.get("/integrations/control-plane")
def cp_root():
    return {
        "integration": "control-plane",
        "mode": "read-only",
        "base_url": control_plane_url(),
        "note": "No POST/execute endpoints exist in Red v2 integration layer."
    }

@router.get("/integrations/control-plane/health")
def cp_health():
    return probe_health()

@router.get("/integrations/control-plane/info")
def cp_info():
    return fetch_info()

@router.get("/integrations/control-plane/runners")
def cp_runners():
    return list_runners()

@router.get("/integrations/control-plane/openapi")
def cp_openapi():
    return fetch_openapi()
