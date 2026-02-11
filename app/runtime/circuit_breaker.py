from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class BreakerConfig:
    max_failures: int = 5
    window_sec: int = 60
    cooldown_sec: int = 300


class CircuitBreaker:
    """
    Simple, deterministic circuit breaker.
    - Counts failures in a rolling window.
    - If max_failures reached => open circuit for cooldown.
    """

    def __init__(self, cfg: BreakerConfig) -> None:
        self.cfg = cfg
        self.window_start_ms = now_ms()
        self.failures = 0
        self.disabled_until_ms: int = 0
        self.last_error: Optional[str] = None

        self.total_failures = 0
        self.total_success = 0
        self.total_skips = 0

    def _in_window(self) -> bool:
        return (now_ms() - self.window_start_ms) < (self.cfg.window_sec * 1000)

    def allow(self) -> bool:
        if now_ms() < self.disabled_until_ms:
            self.total_skips += 1
            return False
        return True

    def record_success(self) -> None:
        self.total_success += 1
        # Lightly heal the failure count within the same window
        if self._in_window():
            self.failures = max(0, self.failures - 1)
        else:
            self.window_start_ms = now_ms()
            self.failures = 0

    def record_failure(self, err: str) -> None:
        self.total_failures += 1
        self.last_error = err[:300]

        if not self._in_window():
            self.window_start_ms = now_ms()
            self.failures = 0

        self.failures += 1
        if self.failures >= self.cfg.max_failures:
            self.disabled_until_ms = now_ms() + (self.cfg.cooldown_sec * 1000)
            # reset window after tripping to avoid immediate retrip post-cooldown
            self.window_start_ms = now_ms()
            self.failures = 0

    def snapshot(self) -> dict:
        return {
            "max_failures": self.cfg.max_failures,
            "window_sec": self.cfg.window_sec,
            "cooldown_sec": self.cfg.cooldown_sec,
            "disabled_until_ms": self.disabled_until_ms or None,
            "last_error": self.last_error,
            "total_success": self.total_success,
            "total_failures": self.total_failures,
            "total_skips": self.total_skips,
        }
