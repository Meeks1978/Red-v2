from __future__ import annotations

import hashlib
import math
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


@dataclass(frozen=True)
class QdrantConfig:
    url: str
    collection: str = "red_memory_semantic"
    dim: int = 384
    timeout_sec: int = 5


class HashEmbedder:
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        tokens = [t for t in (text or "").lower().replace("/", " ").replace(":", " ").split() if t]
        if not tokens:
            return vec

        for t in tokens:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            sign = 1.0 if (h[4] % 2 == 0) else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(v*v for v in vec)) or 1.0
        return [v / norm for v in vec]


def key_to_uuid(key: str) -> str:
    """
    Deterministic UUID for Qdrant point IDs.
    Qdrant in this environment accepts UUID or uint only.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


class SemanticQdrant:
    def __init__(self, cfg: QdrantConfig, embedder: HashEmbedder) -> None:
        self.cfg = cfg
        self.embedder = embedder
        self.s = requests.Session()

    def _u(self, path: str) -> str:
        return self.cfg.url.rstrip("/") + path

    def ensure_collection(self) -> None:
        r = self.s.get(self._u(f"/collections/{self.cfg.collection}"), timeout=self.cfg.timeout_sec)
        if r.status_code == 200:
            return
        payload = {"vectors": {"size": self.cfg.dim, "distance": "Cosine"}}
        cr = self.s.put(self._u(f"/collections/{self.cfg.collection}"), json=payload, timeout=self.cfg.timeout_sec)
        cr.raise_for_status()

    def upsert(self, *, point_id: str, text: str, payload: Dict[str, Any]) -> None:
        """
        Uses UUID point IDs and stores the human key in payload["key"].
        """
        self.ensure_collection()
        vec = self.embedder.embed(text)

        qid = key_to_uuid(point_id)
        payload = dict(payload)
        payload.setdefault("key", point_id)

        body = {"points": [{"id": qid, "vector": vec, "payload": payload}]}

        r = self.s.put(
            self._u(f"/collections/{self.cfg.collection}/points?wait=true"),
            json=body,
            timeout=self.cfg.timeout_sec,
        )
        r.raise_for_status()

    def search(self, *, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        self.ensure_collection()
        vec = self.embedder.embed(query)

        body: Dict[str, Any] = {
            "vector": vec,
            "limit": max(1, min(limit, 20)),
            "with_payload": True,
        }

        r = self.s.post(
            self._u(f"/collections/{self.cfg.collection}/points/search"),
            json=body,
            timeout=self.cfg.timeout_sec,
        )
        r.raise_for_status()
        return r.json().get("result", [])
