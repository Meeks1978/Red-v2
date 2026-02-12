from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ModelTarget:
    tag: str
    base_url: str
    name: str
    timeout_sec: int


@dataclass(frozen=True)
class EngineRoute:
    engine: str
    primary: ModelTarget
    fallbacks: List[ModelTarget]


def build_routes(
    *,
    simrig_url: str,
    aicontrol_url: str = "",
    timeout_planning: int = 30,
    timeout_advisory: int = 30,
    timeout_verify: int = 25,
    timeout_fallback: int = 20,
) -> List[EngineRoute]:
    """
    Fast-first routing. Big models are optional and OFF by default.
    """

    # ---- model selection (env overrides) ----
    planning_model = os.getenv("PLANNING_MODEL", "qwen2.5:14b")
    advisory_model = os.getenv("ADVISORY_MODEL", "qwen2.5:14b")
    verify_model   = os.getenv("VERIFY_MODEL",   "qwen2.5:14b")

    enable_big_planner = os.getenv("ENABLE_BIG_PLANNER", "false").lower() == "true"
    big_planner_model  = os.getenv("BIG_PLANNER_MODEL", "huihui_ai/deepseek-r1-abliterated:32b-qwen-distill")

    # Optional AI-Control fallback model (only if URL is non-empty and reachable)
    aicontrol_fallback_model = os.getenv("AICONTROL_FALLBACK_MODEL", "qwen2.5:7b-instruct-q4_0")

    routes: List[EngineRoute] = []

    # ---- planning route ----
    planning_primary = ModelTarget(
        tag="simrig-planning-fast",
        base_url=simrig_url,
        name=planning_model,
        timeout_sec=timeout_planning,
    )

    planning_fallbacks: List[ModelTarget] = []
    # optional big planner (OFF by default)
    if enable_big_planner:
        planning_fallbacks.append(ModelTarget(
            tag="simrig-planning-big",
            base_url=simrig_url,
            name=big_planner_model,
            timeout_sec=timeout_fallback,
        ))
    # optional AI-Control fallback (only if URL provided)
    if aicontrol_url:
        planning_fallbacks.append(ModelTarget(
            tag="aicontrol-fallback",
            base_url=aicontrol_url,
            name=aicontrol_fallback_model,
            timeout_sec=timeout_fallback,
        ))

    routes.append(EngineRoute(engine="planning", primary=planning_primary, fallbacks=planning_fallbacks))

    # ---- advisory route ----
    advisory_primary = ModelTarget(
        tag="simrig-advisory-fast",
        base_url=simrig_url,
        name=advisory_model,
        timeout_sec=timeout_advisory,
    )
    advisory_fallbacks: List[ModelTarget] = []
    if aicontrol_url:
        advisory_fallbacks.append(ModelTarget(
            tag="aicontrol-fallback",
            base_url=aicontrol_url,
            name=aicontrol_fallback_model,
            timeout_sec=timeout_fallback,
        ))
    routes.append(EngineRoute(engine="advisory", primary=advisory_primary, fallbacks=advisory_fallbacks))

    # ---- verify route ----
    verify_primary = ModelTarget(
        tag="simrig-verify-fast",
        base_url=simrig_url,
        name=verify_model,
        timeout_sec=timeout_verify,
    )
    verify_fallbacks: List[ModelTarget] = []
    if aicontrol_url:
        verify_fallbacks.append(ModelTarget(
            tag="aicontrol-fallback",
            base_url=aicontrol_url,
            name=aicontrol_fallback_model,
            timeout_sec=timeout_fallback,
        ))
    routes.append(EngineRoute(engine="verify", primary=verify_primary, fallbacks=verify_fallbacks))

    return routes


def pick_route(routes: List[EngineRoute], engine: str) -> Optional[EngineRoute]:
    for r in routes:
        if r.engine == engine:
            return r
    return None
