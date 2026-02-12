from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.models.routing import build_routes, pick_route, EngineRoute, ModelTarget


@dataclass(frozen=True)
class GatewayResult:
    ok: bool
    content: str
    used: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    attempts: List[Dict[str, Any]] = None


class ModelGateway:
    """
    Central routing layer for Red engines.

    Contracts relied on by engines:
      - chat(engine, messages, options) -> GatewayResult
      - status() -> dict
    """

    def __init__(self) -> None:
        self.s = requests.Session()

        self.simrig_url = os.getenv("OLLAMA_SIMRIG_URL", "http://ai-simrig:11434").rstrip("/")
        self.aicontrol_url = os.getenv("OLLAMA_AICONTROL_URL", "http://ai-control:11434").rstrip("/")

        # Fast reachability probe so dead backends don't add latency
        sim_ok = self._is_reachable(self.simrig_url, timeout=1.5)
        ai_ok = self._is_reachable(self.aicontrol_url, timeout=1.0)

        # If AI-Control isn't reachable, don't include it in routes at all
        aicontrol_url = self.aicontrol_url if ai_ok else ""

        self.routes = build_routes(
            simrig_url=self.simrig_url,
            aicontrol_url=aicontrol_url,
            timeout_planning=int(os.getenv("LLM_TIMEOUT_PLANNING_SEC", "90")),
            timeout_advisory=int(os.getenv("LLM_TIMEOUT_ADVISORY_SEC", "90")),
            timeout_verify=int(os.getenv("LLM_TIMEOUT_VERIFY_SEC", "60")),
            timeout_fallback=int(os.getenv("LLM_TIMEOUT_FALLBACK_SEC", "45")),
        )

    def _is_reachable(self, base_url: str, timeout: float = 1.5) -> bool:
        if not base_url:
            return False
        try:
            r = self.s.get(base_url.rstrip("/") + "/api/tags", timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    def _ollama_chat(
        self,
        *,
        base_url: str,
        model: str,
        messages: List[Dict[str, str]],
        timeout_sec: int,
        options: Optional[Dict[str, Any]],
    ) -> Tuple[str, Dict[str, Any]]:
        url = base_url.rstrip("/") + "/api/chat"
        payload: Dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        if options:
            payload["options"] = options

        r = self.s.post(url, json=payload, timeout=timeout_sec)
        r.raise_for_status()
        data = r.json()

        msg = data.get("message") or {}
        content = msg.get("content") or ""
        meta = {
            "model": data.get("model", model),
            "created_at": data.get("created_at"),
            "done": data.get("done", True),
            "total_duration": data.get("total_duration"),
            "eval_count": data.get("eval_count"),
            "eval_duration": data.get("eval_duration"),
        }
        return str(content), meta

    def _call_target(
        self,
        *,
        target: ModelTarget,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]],
    ) -> Tuple[bool, str, Dict[str, Any], Optional[str]]:
        t0 = time.time()
        try:
            content, meta = self._ollama_chat(
                base_url=target.base_url,
                model=target.name,
                messages=messages,
                timeout_sec=target.timeout_sec,
                options=options,
            )
            used = {
                "tag": target.tag,
                "base_url": target.base_url,
                "model": target.name,
                "timeout_sec": target.timeout_sec,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "meta": meta,
            }
            return True, content, used, None
        except Exception as e:
            used = {
                "tag": target.tag,
                "base_url": target.base_url,
                "model": target.name,
                "timeout_sec": target.timeout_sec,
                "elapsed_ms": int((time.time() - t0) * 1000),
            }
            return False, "", used, str(e)

    def chat(
        self,
        *,
        engine: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> GatewayResult:
        route = pick_route(self.routes, engine)
        if route is None:
            return GatewayResult(ok=False, content="", error=f"no route for engine={engine}", attempts=[])

        attempts: List[Dict[str, Any]] = []
        targets = [route.primary] + list(route.fallbacks)

        for tgt in targets:
            ok, content, used, err = self._call_target(target=tgt, messages=messages, options=options)
            if ok:
                return GatewayResult(ok=True, content=content, used=used, attempts=attempts)
            attempts.append({"used": used, "error": err})

        return GatewayResult(ok=False, content="", error="all targets failed", attempts=attempts)

    def status(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "simrig_url": self.simrig_url,
            "aicontrol_url": self.aicontrol_url,
            "targets": [],
        }

        def tags_ok(base_url: str, timeout: float = 1.5) -> Tuple[bool, str]:
            try:
                r = self.s.get(base_url.rstrip("/") + "/api/tags", timeout=timeout)
                return (r.status_code == 200), f"status={r.status_code}"
            except Exception as e:
                return False, str(e)

        for r in self.routes:
            for tgt in [r.primary] + list(r.fallbacks):
                ok, note = tags_ok(tgt.base_url, timeout=1.5)
                out["targets"].append({
                    "engine": r.engine,
                    "tag": tgt.tag,
                    "base_url": tgt.base_url,
                    "model": tgt.name,
                    "reachable": ok,
                    "note": note,
                })

        return out


# Import-time singleton expected by engines
GATEWAY = ModelGateway()
