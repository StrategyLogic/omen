"""Scenario condition-set generation helpers."""

from __future__ import annotations

from typing import Any


def build_condition_derivation_trace(
    *,
    scenario_key: str,
    scenario_ontology: dict[str, Any],
    selected_dimensions: dict[str, Any],
    strategic_conditions: dict[str, Any],
) -> dict[str, Any]:
    objective = str(scenario_ontology.get("objective") or "").strip()
    constraints = list(scenario_ontology.get("constraints") or [])
    selected = list(selected_dimensions.get("selected_dimension_keys") or [])
    required = list(strategic_conditions.get("required") or [])

    steps = [
        f"Scenario objective identified: {objective or 'unknown objective'}",
        f"Key constraints interpreted: {', '.join(constraints[:2]) if constraints else 'none'}",
        f"Selected dimensions: {', '.join(selected) if selected else 'none'}",
        f"Condition projection produced required actions: {', '.join(required[:2]) if required else 'none'}",
    ]

    return {
        "scenario_key": scenario_key,
        "ontology_refs": [
            "objective",
            "constraints",
            "tradeoff_pressure",
            "resistance_assumptions",
        ],
        "selected_dimensions": selected,
        "derivation_steps": steps,
        "missing_evidence_reasons": [],
    }
