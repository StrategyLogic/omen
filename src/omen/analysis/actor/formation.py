"""Scenario result assembly helpers for deterministic strategic actor simulation."""

from __future__ import annotations

from typing import Any


def assemble_capability_dilemma_fit(
    *,
    scenario_key: str,
    capability_scores: dict[str, float],
) -> dict[str, Any]:
    if not capability_scores:
        fit = "medium"
    else:
        avg = sum(capability_scores.values()) / max(len(capability_scores), 1)
        fit = "high" if avg >= 0.7 else "low" if avg <= 0.4 else "medium"

    return {
        "scenario_key": scenario_key,
        "fit": fit,
        "capability_scores": capability_scores,
    }
