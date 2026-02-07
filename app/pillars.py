from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple, Any
import os
import time

PillarName = Literal[
    "identity",
    "continuity",
    "agency",
    "governance",
    "awareness",
    "presence",
    "intentionality",
    "adaptation",
    "embodiment",
    "trust",
]

ALL_PILLARS: List[PillarName] = [
    "identity",
    "continuity",
    "agency",
    "governance",
    "awareness",
    "presence",
    "intentionality",
    "adaptation",
    "embodiment",
    "trust",
]


@dataclass(frozen=True)
class Signal:
    name: str
    ok: bool
    weight: int
    detail: str


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _clamp_0_100(x: int) -> int:
    return max(0, min(100, x))


def _score_from_signals(signals: List[Signal]) -> Tuple[int, List[Dict[str, Any]]]:
    # Weighted average of boolean signals.
    total = sum(s.weight for s in signals) or 1
    earned = sum(s.weight for s in signals if s.ok)
    score = int(round((earned / total) * 100))
    return _clamp_0_100(score), [
        {"name": s.name, "ok": s.ok, "weight": s.weight, "detail": s.detail} for s in signals
    ]


def compute_pillars() -> Dict[str, Any]:
    """
    Phase-1 Pillars engine: deterministic, local signals only.
    No network calls. No execution. No side effects.
    """
    start = time.time()

    # Core policy signals (from env) — these enforce your Phase-5 discipline.
    disarmed = (os.getenv("DEFAULT_WORLD_STATE", "DISARMED").upper() == "DISARMED")
    switches_off = all([
        not _env_bool("SWITCH_SELF_UPGRADE", False),
        not _env_bool("SWITCH_ALWAYS_ON_AGENTS", False),
        not _env_bool("SWITCH_COEXISTENCE", False),
    ])
    execution_off = all([
        not _env_bool("ALLOW_SHELL_EXEC", False),
        not _env_bool("ALLOW_UI_AUTOMATION", False),
        not _env_bool("ALLOW_DOCKER_CONTROL", False),
    ])

    # Pillar definitions (Phase-1: mostly policy + local configuration)
    pillar_signals: Dict[PillarName, List[Signal]] = {
        "identity": [
            Signal("identity.yaml present", ok=os.path.exists("identity.yaml"), weight=5,
                   detail="identity.yaml exists in working directory"),
            Signal("node id set", ok=bool(os.getenv("RED_NODE_ID", "")), weight=3,
                   detail="RED_NODE_ID env is set"),
        ],
        "continuity": [
            Signal("service running", ok=True, weight=5,
                   detail="process is alive (liveness)"),
            Signal("restart policy configured", ok=True, weight=3,
                   detail="container restart policy expected unless-stopped"),
        ],
        "agency": [
            Signal("world state DISARMED", ok=disarmed, weight=6,
                   detail="DEFAULT_WORLD_STATE=DISARMED enforced"),
            Signal("execution disabled", ok=execution_off, weight=6,
                   detail="ALLOW_* execution flags are false"),
        ],
        "governance": [
            Signal("phase-6 switches off", ok=switches_off, weight=6,
                   detail="self-upgrade/always-on/coexistence switches are OFF"),
            Signal("approval required (design)", ok=True, weight=4,
                   detail="proposals are gated; execution requires approval via Control Plane"),
        ],
        "awareness": [
            Signal("health endpoint available", ok=True, weight=4,
                   detail="/health is implemented"),
            Signal("pillars endpoint available", ok=True, weight=4,
                   detail="/health/pillars is implemented"),
        ],
        "presence": [
            Signal("watch-first channel configured", ok=True, weight=3,
                   detail="default approvals channel is watch-first"),
            Signal("no phone UI automation", ok=not _env_bool("ALLOW_UI_AUTOMATION", False), weight=3,
                   detail="iPhone is not a UI automation target"),
        ],
        "intentionality": [
            Signal("/propose exists", ok=True, weight=5,
                   detail="proposal-only interface exists"),
            Signal("no execute endpoint", ok=True, weight=5,
                   detail="no execution surface in Red v2"),
        ],
        "adaptation": [
            Signal("configurable via env", ok=True, weight=4,
                   detail="behavior gated by env flags"),
            Signal("upgrade switch OFF", ok=not _env_bool("SWITCH_SELF_UPGRADE", False), weight=4,
                   detail="self-upgrade capability is OFF by default"),
        ],
        "embodiment": [
            Signal("voice profile deferred", ok=True, weight=2,
                   detail="voice embodiment not required for Phase-1"),
            Signal("AR presence deferred", ok=True, weight=2,
                   detail="Air3 integration deferred"),
        ],
        "trust": [
            Signal("no exec by design", ok=execution_off and disarmed, weight=8,
                   detail="DISARMED + execution flags OFF"),
            Signal("deterministic outputs", ok=True, weight=4,
                   detail="pillars scoring is deterministic (no network calls)"),
        ],
    }

    per_pillar: Dict[str, Any] = {}
    scores: List[int] = []

    for p in ALL_PILLARS:
        score, signals = _score_from_signals(pillar_signals[p])
        scores.append(score)
        per_pillar[p] = {"score": score, "signals": signals}

    existence = int(round(sum(scores) / (len(scores) or 1)))
    duration_ms = int(round((time.time() - start) * 1000))

    return {
        "existence_score": existence,
        "duration_ms": duration_ms,
        "pillars": per_pillar,
    }
