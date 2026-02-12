import os
import time
import requests

BASE = os.getenv("RED_BASE", "http://127.0.0.1:8111")

def _get(path: str):
    r = requests.get(BASE + path, timeout=8)
    r.raise_for_status()
    return r.json()

def _post(path: str, payload: dict):
    r = requests.post(BASE + path, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

def test_bu4_health_ok():
    j = _get("/health")
    assert j.get("ok") is True

def test_bu4_snapshot_contract():
    j = _get("/v1/world/snapshot")
    assert j.get("ok") is True
    store = j.get("store") or {}
    assert isinstance(store.get("db_path"), str) and store["db_path"]
    counts = j.get("counts") or {}
    # counts must exist and be ints
    assert isinstance(counts.get("entities"), int)
    assert isinstance(counts.get("events"), int)

def test_bu4_entity_upsert_and_drift_changes():
    # baseline drift fingerprint
    d0 = _get("/v1/world/drift?limit=10")
    assert d0.get("ok") is True
    fp0 = d0.get("fingerprint")
    assert isinstance(fp0, str) and fp0

    # upsert entity (should not 500)
    ent_id = f"bu4_lock_x1_{int(time.time())}"
    up = _post("/v1/world/entities", {
        "entity_id": ent_id,
        "kind": "service",
        "attrs": {"k": "v1"}
    })
    assert up.get("ok") is True
    ent = up.get("entity") or {}
    assert ent.get("entity_id") == ent_id

    # drift should react to change
    d1 = _get("/v1/world/drift?limit=10")
    assert d1.get("ok") is True
    fp1 = d1.get("fingerprint")
    assert isinstance(fp1, str) and fp1
    assert fp1 != fp0

    # drift_events should include at least one entry when fingerprint changes
    ev = d1.get("drift_events") or []
    assert isinstance(ev, list)
    assert len(ev) >= 1
