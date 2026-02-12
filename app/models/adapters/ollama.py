from __future__ import annotations

import requests
from typing import Any, Dict, List, Optional, Tuple


class OllamaAdapter:
    """
    Minimal Ollama /api/chat adapter.
    """
    def __init__(self) -> None:
        self.s = requests.Session()

    def chat(
        self,
        *,
        base_url: str,
        model: str,
        messages: List[Dict[str, str]],
        timeout_sec: int = 60,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        url = base_url.rstrip("/") + "/api/chat"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options

        r = self.s.post(url, json=payload, timeout=timeout_sec)
        r.raise_for_status()
        data = r.json()

        # Ollama returns {"message":{"role":"assistant","content":"..."}, ...}
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
