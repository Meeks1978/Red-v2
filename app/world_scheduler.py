from __future__ import annotations

import os
import threading
import time
from typing import Optional, Dict, Any

from app.world_probes import run_probes


def _env_bool(name: str, default: str = "0") -> bool:
    v = os.getenv(name, default).strip().lower()
    return v in ("1", "true", "yes", "on")


def _env_float(name: str, default: str) -> float:
    try:
        return float(os.getenv(name, default))
    except Exception:
        return float(default)


class WorldScheduler:
    """
    World Engine 4 scheduler:
      - Periodically runs probes
      - Optional enforcement (auto-freeze)
    Safe-by-default: OFF unless WORLD_SCHEDULER_ENABLED=1
    """

    def __init__(self):
        self.enabled = _env_bool("WORLD_SCHEDULER_ENABLED", "0")
        self.interval_s = _env_float("WORLD_SCHEDULER_INTERVAL_S", "10")
        self.enforce_freeze = _env_bool("WORLD_SCHEDULER_ENFORCE_FREEZE", "1")

        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._last_result: Optional[Dict[str, Any]] = None

    def start(self) -> None:
        if not self.enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="world-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "interval_s": self.interval_s,
            "enforce_freeze": self.enforce_freeze,
            "running": bool(self._thread and self._thread.is_alive()),
            "last_result": self._last_result,
        }

    def _loop(self) -> None:
        # jitter a bit so restarts don’t align perfectly
        time.sleep(1.0)
        while not self._stop.is_set():
            try:
                self._last_result = run_probes(enforce_freeze=self.enforce_freeze)
            except Exception as e:
                self._last_result = {"ok": False, "error": str(e)}
            self._stop.wait(self.interval_s)


SCHEDULER = WorldScheduler()
