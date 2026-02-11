from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import requests


def _env_true(name: str) -> bool:
    return os.getenv(name, "").lower() == "true"


def _middleware_names(app) -> List[str]:
    try:
        return [m.cls.__name__ for m in getattr(app, "user_middleware", [])]
    except Exception:
        return []


def _qdrant_get(url: str, path: str, timeout: int = 3) -> requests.Response:
    return requests.get(url.rstrip("/") + path, timeout=timeout)


def _qdrant_collection_dim(url: str, collection: str) -> Optional[int]:
    try:
        r = _qdrant_get(url, f"/collections/{collection}", timeout=4)
        if r.status_code != 200:
            return None
        data = r.json()
        # Qdrant returns: result.config.params.vectors.size
        return int(data["result"]["config"]["params"]["vectors"]["size"])
    except Exception:
        return None


def _qdrant_ok(url: str) -> bool:
    try:
        r = _qdrant_get(url, "/collections", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _embed_dim(semantic_memory: Any) -> Optional[int]:
    """
    Uses the embedder to create a tiny embedding and reads its length.
    """
    try:
        emb = getattr(semantic_memory, "embedder", None)
        if emb is None:
            return None
        v = emb.embed("dim_check")
        return len(v)
    except Exception:
        return None


def startup_invariants(app, container) -> Dict[str, Any]:
    """
    Returns a dict of invariant results. If INVARIANTS_STRICT=true, raises on failure.
    """
    strict = _env_true("INVARIANTS_STRICT")

    enabled_observer = _env_true("ENABLE_SHADOW_OBSERVER")
    enabled_bu3 = _env_true("ENABLE_BU3_INGEST")
    enabled_sem = _env_true("ENABLE_SEMANTIC_MEMORY")

    names = _middleware_names(app)
    has_ingest = any("Ingest" in n for n in names)  # MemoryIngestMiddleware
    has_observer = any("Observer" in n for n in names)  # ShadowObserverMiddleware

    # Basic checks
    failures: List[str] = []
    if enabled_bu3 and not has_ingest:
        failures.append("ENABLE_BU3_INGEST=true but ingest middleware not attached")
    if enabled_observer and not has_observer:
        failures.append("ENABLE_SHADOW_OBSERVER=true but observer middleware not attached")

    # Semantic checks (only if enabled)
    qdrant_url = os.getenv("QDRANT_URL", "")
    qdrant_collection = os.getenv("QDRANT_COLLECTION", "red_memory_semantic")
    qdrant_dim = int(os.getenv("QDRANT_DIM", "384"))

    qdrant_reachable = None
    collection_dim = None
    embed_dim = None
    dim_match = None

    if enabled_sem:
        if not qdrant_url:
            failures.append("ENABLE_SEMANTIC_MEMORY=true but QDRANT_URL is not set")
        else:
            qdrant_reachable = _qdrant_ok(qdrant_url)
            if not qdrant_reachable:
                failures.append(f"Qdrant not reachable at {qdrant_url}")
            else:
                collection_dim = _qdrant_collection_dim(qdrant_url, qdrant_collection)
                if collection_dim is None:
                    # not fatal: collection may be auto-created on first upsert
                    pass
                embed_dim = _embed_dim(getattr(container, "semantic_memory", None))
                if embed_dim is None:
                    failures.append("Semantic embedder not available or embed failed")
                else:
                    # If collection exists, enforce exact match; otherwise enforce embedder matches env dim
                    dim_match = (embed_dim == qdrant_dim) if collection_dim is None else (embed_dim == collection_dim)
                    if not dim_match:
                        failures.append(
                            f"Semantic dim mismatch: embed_dim={embed_dim}, env_qdrant_dim={qdrant_dim}, collection_dim={collection_dim}"
                        )

    result = {
        "ok": len(failures) == 0,
        "strict": strict,
        "middleware": {
            "attached": names,
            "has_ingest": has_ingest,
            "has_observer": has_observer,
        },
        "flags": {
            "ENABLE_SHADOW_OBSERVER": enabled_observer,
            "ENABLE_BU3_INGEST": enabled_bu3,
            "ENABLE_SEMANTIC_MEMORY": enabled_sem,
        },
        "semantic": {
            "qdrant_url_set": bool(qdrant_url),
            "qdrant_url": qdrant_url or None,
            "collection": qdrant_collection,
            "env_dim": qdrant_dim,
            "qdrant_reachable": qdrant_reachable,
            "collection_dim": collection_dim,
            "embed_dim": embed_dim,
            "dim_match": dim_match,
        },
        "failures": failures,
        "ts_ms": int(time.time() * 1000),
    }

    if strict and failures:
        raise RuntimeError("Startup invariants failed: " + " | ".join(failures))

    if failures:
        print({"invariants_failed": failures})

    return result
