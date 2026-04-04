"""Build scenario ontology artifacts from situation source documents."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from omen.scenario.ingest_validator import DeferredScopeFeatureError


_DEFAULT_OBJECTIVES = {
    "A": "Stabilize core platform control while restoring execution momentum.",
    "B": "Improve survival probability through open-ecosystem scale leverage.",
    "C": "Maximize short-term strategic stability via external platform alliance.",
}

_DEFAULT_TRADEOFFS = {
    "A": ["Execution speed vs platform completeness", "Short-term revenue vs long-term control"],
    "B": ["Scale expansion vs differentiation", "Platform dependence vs bargaining power"],
    "C": ["Short-term stability vs long-term autonomy", "Transaction efficiency vs strategic freedom"],
}

_DEFAULT_RESISTANCE = {
    "A": (0.8, 0.7, 0.6, 0.7),
    "B": (0.5, 0.5, 0.5, 0.4),
    "C": (0.4, 0.4, 0.5, 0.3),
}

_DEFERRED_DYNAMIC_MARKERS = {
    "dynamic_authoring",
    "dynamic_scenarios",
    "free_form_scenarios",
    "scenario_generator",
}

_DEFERRED_ENTERPRISE_MARKERS = {
    "enterprise_resistance_extensions",
    "enterprise_template_catalog",
    "resistance_extension_profiles",
    "custom_resistance_dimensions",
    "enterprise_resistance_profile",
}


def _extract_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        lines.append(line)
    return lines


def _build_constraints(base_lines: list[str], scenario_key: str) -> list[str]:
    top = base_lines[:2]
    if scenario_key == "A":
        hint = "Prioritize internal platform continuity under execution pressure"
    elif scenario_key == "B":
        hint = "Prioritize ecosystem access while controlling commoditization risk"
    else:
        hint = "Prioritize alliance efficiency with explicit autonomy safeguards"

    constraints = top + [hint]
    return constraints if constraints else ["Constraint context is missing in source document"]


def _validate_source_scope_or_raise(text: str) -> None:
    lowered = text.lower()
    for marker in _DEFERRED_DYNAMIC_MARKERS:
        if marker in lowered:
            raise DeferredScopeFeatureError(
                f"`{marker}` is deferred scope in this release. "
                "Only deterministic A/B/C scenario packs are supported."
            )

    for marker in _DEFERRED_ENTERPRISE_MARKERS:
        if marker in lowered:
            raise DeferredScopeFeatureError(
                f"`{marker}` is deferred scope. Enterprise resistance extensions are not supported in this release."
            )


def build_scenario_ontology_from_situation(
    *,
    situation_file: str | Path,
    actor_ref: str,
    pack_id: str,
    pack_version: str,
) -> dict:
    path = Path(situation_file)
    text = path.read_text(encoding="utf-8")
    _validate_source_scope_or_raise(text)
    lines = _extract_lines(text)
    excerpt = " ".join(lines[:3])[:200]
    situation_id = path.stem

    scenarios: list[dict] = []
    for key in ("A", "B", "C"):
        v = _DEFAULT_RESISTANCE[key]
        aggregate = round(sum(v) / 4.0, 3)
        scenarios.append(
            {
                "scenario_key": key,
                "title": f"Scenario {key}",
                "objective": _DEFAULT_OBJECTIVES[key],
                "constraints": _build_constraints(lines, key),
                "tradeoff_pressure": _DEFAULT_TRADEOFFS[key],
                "resistance_assumptions": {
                    "structural_conflict": v[0],
                    "resource_reallocation_drag": v[1],
                    "cultural_misalignment": v[2],
                    "veto_node_intensity": v[3],
                    "aggregate_resistance": aggregate,
                    "assumption_rationale": [
                        f"Derived from situation source: {path}",
                        f"Actor reference: {actor_ref}",
                    ],
                },
                "modeling_notes": [
                    f"Situation excerpt: {excerpt}" if excerpt else "No source excerpt extracted",
                    "Scenario generated with deterministic slot policy A/B/C",
                ],
            }
        )

    return {
        "pack_id": pack_id,
        "pack_version": pack_version,
        "derived_from_situation_id": situation_id,
        "ontology_version": "scenario_ontology_v1",
        "scenarios": scenarios,
        "source_meta": {
            "source_path": str(path),
            "generated_at": datetime.now().isoformat(),
        },
    }


def scenario_ontology_to_deterministic_pack(ontology: dict) -> dict:
    scenarios = []
    for scenario in ontology.get("scenarios", []):
        scenarios.append(
            {
                "scenario_key": scenario["scenario_key"],
                "title": scenario["title"],
                "target_outcome": scenario["objective"],
                "constraints": list(scenario.get("constraints") or []),
                "dilemma_tradeoffs": list(scenario.get("tradeoff_pressure") or []),
                "resistance_baseline": {
                    "structural_conflict": scenario["resistance_assumptions"]["structural_conflict"],
                    "resource_reallocation_drag": scenario["resistance_assumptions"]["resource_reallocation_drag"],
                    "cultural_misalignment": scenario["resistance_assumptions"]["cultural_misalignment"],
                    "veto_node_intensity": scenario["resistance_assumptions"]["veto_node_intensity"],
                    "aggregate_resistance": scenario["resistance_assumptions"]["aggregate_resistance"],
                },
            }
        )

    return {
        "pack_id": ontology["pack_id"],
        "pack_version": ontology["pack_version"],
        "scenarios": scenarios,
    }
