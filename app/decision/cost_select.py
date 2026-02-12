from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

@dataclass(frozen=True)
class CostWeights:
    w_risk: float = 1.0
    w_time: float = 0.5
    w_complexity: float = 0.3
    w_reversibility: float = 0.7
    w_confidence: float = 0.2

    @staticmethod
    def from_env() -> "CostWeights":
        def f(k: str, d: float) -> float:
            v = os.getenv(k)
            return d if v is None else float(v)
        return CostWeights(
            w_risk=f("COST_W_RISK", 1.0),
            w_time=f("COST_W_TIME", 0.5),
            w_complexity=f("COST_W_COMPLEXITY", 0.3),
            w_reversibility=f("COST_W_REVERSIBILITY", 0.7),
            w_confidence=f("COST_W_CONFIDENCE", 0.2),
        )

def _norm(vals: List[float]) -> List[float]:
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        return [0.5] * len(vals)
    return [(v - lo) / (hi - lo) for v in vals]

def score_variants(
    variants: List[Dict[str, Any]],
    *,
    weights: CostWeights,
) -> Tuple[int, Dict[str, Any]]:

    risk = [float(v.get("risk", 0.5)) for v in variants]
    time_raw = [float(v.get("time_est_min", 1.0)) for v in variants]
    comp = [float(v.get("complexity", 0.5)) for v in variants]
    rev = [float(v.get("reversibility", 0.5)) for v in variants]
    conf = [float(v.get("confidence", 0.5)) for v in variants]

    time_norm = _norm(time_raw)

    scores = []
    rows = []

    for i, v in enumerate(variants):
        s = (
            weights.w_risk * risk[i]
            + weights.w_time * time_norm[i]
            + weights.w_complexity * comp[i]
            - weights.w_reversibility * rev[i]
            - weights.w_confidence * conf[i]
        )
        scores.append(s)
        rows.append({
            "name": v.get("name"),
            "score": s,
            "risk": risk[i],
            "time_est_min": time_raw[i],
            "complexity": comp[i],
            "reversibility": rev[i],
            "confidence": conf[i],
        })

    best = min(range(len(scores)), key=lambda i: scores[i])

    debug = {
        "selected_rule": "weighted_cost(min_score)",
        "weights": weights.__dict__,
        "rows": sorted(rows, key=lambda r: r["score"]),
        "selected": rows[best],
    }

    return best, debug
