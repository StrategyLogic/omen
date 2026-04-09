"""Actor derivation helpers for deterministic scenario simulation."""

from __future__ import annotations

from typing import Any

from omen.analysis.actor.strategy import (
    calculate_strategic_freedom_factor,
    generate_condition_sets,
)


def get_simulate_reasoning_order() -> tuple[str, ...]:
    return (
        "seed",
        "constraint_activation",
        "target_or_objective",
        "gap",
        "required_or_warning_or_blocking",
    )


def derive_actor_path(
    *,
    scenario_key: str,
    actor_profile_ref: str,
    scenario_ontology: dict[str, Any],
    selected_dimensions: dict[str, Any],
    capability_scores: dict[str, float],
    capability_fit: str,
) -> dict[str, Any]:
    objective = str(scenario_ontology.get("objective") or "").strip()
    constraints = [str(item).strip() for item in (scenario_ontology.get("constraints") or []) if str(item).strip()]
    selected = [str(item).strip() for item in (selected_dimensions.get("selected_dimension_keys") or []) if str(item).strip()]

    ranked = sorted(capability_scores.items(), key=lambda item: item[1], reverse=True)
    dominant_capability = ranked[0][0] if ranked else "capability_unknown"
    style = {
        "A": "offense_breakthrough",
        "B": "defense_resilience",
        "C": "confrontation_competition",
    }.get(scenario_key, "balanced")

    return {
        "scenario_key": scenario_key,
        "actor_profile_ref": actor_profile_ref,
        "decision_style": style,
        "dominant_capability": dominant_capability,
        "selected_dimensions": selected,
        "objective_alignment": objective or "objective_not_provided",
        "constraint_focus": constraints[:2],
        "derivation_notes": [
            f"Derive actor path from planned scene {scenario_key}",
            f"Capability fit level: {capability_fit}",
            f"Primary capability anchor: {dominant_capability}",
        ],
    }


def derive_strategic_freedom_conditions(
    *,
    scenario_key: str,
    actor_derivation: dict[str, Any],
    selected_dimensions: dict[str, Any],
    resistance_baseline: dict[str, Any],
    capability_fit: str,
) -> dict[str, Any]:
    score = calculate_strategic_freedom_factor(
        capability_fit=capability_fit,
        resistance_baseline=resistance_baseline,
    )
    conditions = generate_condition_sets(
        scenario_key=scenario_key,
        strategic_freedom_score=score,
        resistance_baseline=resistance_baseline,
    )

    selected = [str(item).strip() for item in (selected_dimensions.get("selected_dimension_keys") or []) if str(item).strip()]
    style = str(actor_derivation.get("decision_style") or "balanced")
    if selected:
        conditions["required"].append(
            f"围绕关键能力维度执行: {', '.join(selected[:2])}"
        )
    conditions["required"].append(f"执行决策风格: {style}")
    conditions["reasoning_order"] = list(get_simulate_reasoning_order())
    return conditions
