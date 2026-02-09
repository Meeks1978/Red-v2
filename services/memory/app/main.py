import os
from fastapi import FastAPI, HTTPException
from .db import connect, apply_migration
from .models import MemoryPut, MemoryQuery, WorldStatePut
from .store import put_memory, query_memory, world_state_get, world_state_set

app = FastAPI(title="Red Memory Service", version="0.1.0")

@app.on_event("startup")
def startup():
    conn = connect()
    try:
        apply_migration(
            conn,
            os.getenv("RED_MEMORY_MIGRATION", "/app/migrations/001_init.sql"),
        )
    finally:
        conn.close()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/v1/memory/put")
def memory_put(item: MemoryPut):
    try:
        return put_memory(item)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/memory/query")
def memory_query(q: MemoryQuery):
    return query_memory(q)

@app.get("/v1/world/get")
def world_get():
    return world_state_get()

@app.post("/v1/world/set")
def world_set(w: WorldStatePut):
    world_state_set(w)
    return {"ok": True}
