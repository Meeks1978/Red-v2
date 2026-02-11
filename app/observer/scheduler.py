from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class SchedulerConfig:
    enabled: bool = False               # default OFF
    interval_sec: int = 60              # default 60s
    max_ticks: int = 0                  # 0 = unlimited (still bounded by stop)
    daemon: bool = True


class ShadowObserverScheduler:
    """
    Silent scheduler for Shadow Observer.
    - Runs only if enabled
    - Can be stopped cleanly
    - Optional max_ticks for bounded runs
    """

    def __init__(self, config: SchedulerConfig, tick_fn: Callable[[], None]) -> None:
        self.config = config
        self._tick_fn = tick_fn
        self._stop_evt = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if not self.config.enabled:
            return
        if self._thread and self._thread.is_alive():
            return

        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, daemon=self.config.daemon)
        self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        ticks = 0
        while not self._stop_evt.is_set():
            try:
                self._tick_fn()
            except Exception as e:
                # Silent mode: log only; never raise
                print({"observer": "shadow", "error": str(e)})

            ticks += 1
            if self.config.max_ticks and ticks >= self.config.max_ticks:
                break

            # Sleep in small chunks so stop is responsive
            end = time.time() + self.config.interval_sec
            while time.time() < end and not self._stop_evt.is_set():
                time.sleep(0.25)
