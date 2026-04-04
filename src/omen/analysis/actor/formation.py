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


def project_scenario_selected_dimensions(
    *,
    scenario_key: str,
    capability_scores: dict[str, float],
) -> dict[str, Any]:
    ranked = sorted(capability_scores.items(), key=lambda item: item[1], reverse=True)
    selected = [key for key, _ in ranked[:2]] if ranked else []

    if scenario_key == "A":
        rationale = [
            "Prioritize internal platform continuity dimensions for high-control path",
            "Select strongest capability dimensions to reduce execution stall risk",
        ]
    elif scenario_key == "B":
        rationale = [
            "Prioritize ecosystem-adaptation dimensions for open-alliance path",
            "Select dimensions balancing scale gain and differentiation preservation",
        ]
    else:
        rationale = [
            "Prioritize alliance-efficiency dimensions for external-platform path",
            "Select dimensions supporting short-term stability under dependency risk",
        ]

    return {
        "scenario_key": scenario_key,
        "selected_dimension_keys": selected,
        "selection_rationale": rationale,
    }
