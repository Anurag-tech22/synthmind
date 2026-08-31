"""Quantitative Calculation & Sensitivity Engine.

Provides deterministic, reproducible analytical computations that
complement the LLM's qualitative reasoning:

  • Multi-Criteria Decision Analysis (MCDA) with normalized weighted scoring
  • Sensitivity analysis (Best / Base / Worst case scenarios)
  • Weight recalculation for interactive frontend sliders
"""

from __future__ import annotations

from typing import Any


def recalculate_matrix(
    criteria: list[dict[str, Any]],
    options: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Recalculate weighted totals for a Decision Matrix.

    Each criterion has {"name": str, "weight": int (0-100)}.
    Each option has {"name": str, "scores": {criterion_name: int (0-10)}}.

    Returns the options list with updated "total_weighted" and "rank".
    """
    total_weight = sum(c.get("weight", 0) for c in criteria) or 1

    for opt in options:
        scores = opt.get("scores", {})
        weighted_sum = 0.0
        for c in criteria:
            cname = c["name"]
            raw_score = scores.get(cname, 5)  # default mid-score
            weight_fraction = c.get("weight", 0) / total_weight
            weighted_sum += raw_score * weight_fraction
        opt["total_weighted"] = round(weighted_sum, 2)

    # Assign ranks (1 = best)
    ranked = sorted(options, key=lambda o: o["total_weighted"], reverse=True)
    for rank_idx, opt in enumerate(ranked, start=1):
        opt["rank"] = rank_idx

    return options


def sensitivity_analysis(
    criteria: list[dict[str, Any]],
    options: list[dict[str, Any]],
    target_criterion: str,
    swing_pct: int = 20,
) -> dict[str, Any]:
    """Run a sensitivity sweep on a single criterion weight.

    Produces three scenarios (optimistic, base, pessimistic) by varying
    the target criterion's weight by ±swing_pct percentage points.
    """
    base_weight = None
    for c in criteria:
        if c["name"] == target_criterion:
            base_weight = c["weight"]
            break

    if base_weight is None:
        return {"error": f"Criterion '{target_criterion}' not found."}

    scenarios: dict[str, Any] = {}
    for label, delta in [("optimistic", swing_pct), ("base", 0), ("pessimistic", -swing_pct)]:
        tweaked = []
        for c in criteria:
            tweaked_c = dict(c)
            if c["name"] == target_criterion:
                tweaked_c["weight"] = max(0, min(100, base_weight + delta))
            tweaked.append(tweaked_c)

        results = recalculate_matrix(tweaked, [dict(o) for o in options])
        scenarios[label] = {
            "weight_used": max(0, min(100, base_weight + delta)),
            "results": [
                {"name": o["name"], "total_weighted": o["total_weighted"], "rank": o["rank"]}
                for o in results
            ],
        }

    return {
        "criterion": target_criterion,
        "base_weight": base_weight,
        "swing_pct": swing_pct,
        "scenarios": scenarios,
    }


def compute_confidence_bucket(score: int) -> str:
    """Return a human-friendly label for a 0-100 confidence score."""
    if score >= 90:
        return "Very High"
    if score >= 75:
        return "High"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Low"
    return "Very Low"
