"""Actor simulation helpers for deterministic scenario runs."""

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


def build_actor_derivation_trace(
    *,
    scenario_key: str,
    scenario_ontology: dict[str, Any],
    actor_derivation: dict[str, Any],
    selected_dimensions: dict[str, Any],
    strategic_conditions: dict[str, Any],
    missing_evidence_reasons: list[str],
) -> dict[str, Any]:
    objective = str(scenario_ontology.get("objective") or "").strip()
    constraints = [str(item).strip() for item in (scenario_ontology.get("constraints") or []) if str(item).strip()]
    selected = [str(item).strip() for item in (selected_dimensions.get("selected_dimension_keys") or []) if str(item).strip()]
    required = [str(item).strip() for item in (strategic_conditions.get("required") or []) if str(item).strip()]
    derivation_keys = sorted(str(key) for key in actor_derivation.keys()) if isinstance(actor_derivation, dict) else []

    return {
        "scenario_key": scenario_key,
        "ontology_refs": [
            "objective",
            "constraints",
            "tradeoff_pressure",
            "resistance_assumptions",
        ],
        "selected_dimensions": selected,
        "actor_derivation_refs": [f"actor_derivation::{scenario_key}"],
        "derivation_steps": [
            f"Scene objective aligned: {objective or 'unknown objective'}",
            f"Scene constraints interpreted: {', '.join(constraints[:2]) if constraints else 'none'}",
            f"Actor derivation selected dimensions: {', '.join(selected) if selected else 'none'}",
            f"Actor derivation fields observed: {', '.join(derivation_keys[:3]) if derivation_keys else 'none'}",
            f"Strategic condition projection: {', '.join(required[:2]) if required else 'none'}",
        ],
        "missing_evidence_reasons": list(missing_evidence_reasons),
    }


def build_actor_derivation_artifact(
    *,
    run_id: str,
    actor_profile_ref: str,
    scenario_pack_ref: str,
    scenario_derivations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "actor_derivation",
        "version": "actor_derivation_v1",
        "run_id": run_id,
        "actor_profile_ref": actor_profile_ref,
        "scenario_pack_ref": scenario_pack_ref,
        "scenario_derivations": scenario_derivations,
    }


def build_comparability_metadata(
    *,
    actor_profile_version: str,
    scenario_pack_version: str,
    calculation_policy_version: str,
    blocking_reasons: list[str] | None = None,
    executed_order: list[str] | None = None,
    required_order: tuple[str, ...] = ("A", "B", "C"),
) -> dict[str, Any]:
    reasons = list(blocking_reasons or [])
    if executed_order is not None:
        expected = list(required_order)
        if list(executed_order) != expected:
            reasons.append(
                f"scenario order mismatch: expected {expected}, got {list(executed_order)}"
            )
    return {
        "comparable": len(reasons) == 0,
        "blocking_reasons": reasons,
        "actor_profile_version": actor_profile_version,
        "scenario_pack_version": scenario_pack_version,
        "calculation_policy_version": calculation_policy_version,
    }
