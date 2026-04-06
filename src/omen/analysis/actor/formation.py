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
    scenario_ontology: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ranked = sorted(capability_scores.items(), key=lambda item: item[1], reverse=True)
    selected = [key for key, _ in ranked[:2]] if ranked else []

    scene = scenario_ontology or {}
    objective = str(scene.get("objective") or "").strip()
    constraints = [str(item).strip() for item in (scene.get("constraints") or []) if str(item).strip()]
    tradeoff_pressure = [str(item).strip() for item in (scene.get("tradeoff_pressure") or []) if str(item).strip()]

    if scenario_key == "A":
        rationale = [
            "Prioritize offense dimensions from planned scene objective and constraints",
            f"Objective alignment: {objective or 'offense objective from scene'}",
        ]
    elif scenario_key == "B":
        rationale = [
            "Prioritize defense dimensions under planned hard-constraint pressure",
            f"Constraint focus: {', '.join(constraints[:2]) if constraints else 'defense constraints'}",
        ]
    else:
        rationale = [
            "Prioritize confrontation dimensions under direct rivalry tradeoff pressure",
            f"Tradeoff focus: {', '.join(tradeoff_pressure[:2]) if tradeoff_pressure else 'confrontation tradeoff'}",
        ]

    if selected:
        rationale.append(f"Selected highest-capability dimensions: {', '.join(selected)}")

    return {
        "scenario_key": scenario_key,
        "selected_dimension_keys": selected,
        "selection_rationale": rationale,
    }
