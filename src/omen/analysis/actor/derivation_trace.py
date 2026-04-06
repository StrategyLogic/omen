"""Actor derivation trace helpers."""

from __future__ import annotations

from typing import Any


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
