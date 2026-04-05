"""Build and render situation/scenario artifacts for deterministic simulation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from omen.ingest.reportor.situation_brief import render_situation_brief
from omen.scenario.ingest_validator import DeferredScopeFeatureError
from omen.scenario.splitter import normalize_llm_scenarios_with_policy


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


def validate_situation_source_or_raise(situation_file: str | Path) -> None:
    text = Path(situation_file).read_text(encoding="utf-8")
    _validate_source_scope_or_raise(text)


def build_scenario_ontology_from_situation_artifact(
    *,
    situation_artifact: dict[str, Any],
    llm_decomposition: dict[str, Any],
    pack_id: str,
    pack_version: str,
) -> dict[str, Any]:
    scenarios = normalize_llm_scenarios_with_policy(
        list(llm_decomposition.get("scenarios") or []),
        source_hint=f"Derived from situation artifact: {situation_artifact.get('id', 'unknown')}",
    )
    source_meta = dict(llm_decomposition.get("source_meta") or {})
    source_meta.setdefault(
        "source_path",
        str((situation_artifact.get("source_meta") or {}).get("source_path") or ""),
    )
    source_meta.setdefault("generated_at", datetime.now().isoformat())
    source_meta["generated_from"] = "situation_artifact"

    return {
        "pack_id": pack_id,
        "pack_version": pack_version,
        "derived_from_situation_id": str(situation_artifact.get("id") or "unknown"),
        "ontology_version": str(llm_decomposition.get("ontology_version") or "scenario_ontology_v1"),
        "scenarios": scenarios,
        "source_meta": source_meta,
    }


def situation_artifact_to_markdown(situation: dict[str, Any], config_path: str = "config/llm.toml") -> str:
    return render_situation_brief(situation, config_path=config_path)


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


def scenario_ontology_to_markdown(ontology: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Scenario Ontology: {ontology.get('derived_from_situation_id', 'unknown')}")
    lines.append("")
    lines.append(f"- pack_id: {ontology.get('pack_id', 'unknown')}")
    lines.append(f"- pack_version: {ontology.get('pack_version', 'unknown')}")
    lines.append(f"- ontology_version: {ontology.get('ontology_version', 'unknown')}")

    source_meta = ontology.get("source_meta") or {}
    source_path = source_meta.get("source_path")
    if source_path:
        lines.append(f"- source_path: {source_path}")
    generated_at = source_meta.get("generated_at")
    if generated_at:
        lines.append(f"- generated_at: {generated_at}")

    for scenario in ontology.get("scenarios", []):
        key = scenario.get("scenario_key", "?")
        title = scenario.get("title", "")
        lines.append("")
        lines.append(f"## Scenario {key}: {title}")
        lines.append("")
        lines.append(f"- goal: {scenario.get('goal', '')}")
        lines.append(f"- target: {scenario.get('target', '')}")
        lines.append(f"- objective: {scenario.get('objective', '')}")

        variables = scenario.get("variables") or []
        lines.append("- variables:")
        for item in variables:
            name = str(item.get("name") or "unknown")
            vtype = str(item.get("type") or "unknown")
            lines.append(f"  - {name} ({vtype})")

        constraints = scenario.get("constraints") or []
        lines.append("- constraints:")
        for item in constraints:
            lines.append(f"  - {item}")

        tradeoffs = scenario.get("tradeoff_pressure") or []
        lines.append("- tradeoff_pressure:")
        for item in tradeoffs:
            lines.append(f"  - {item}")

        resistance = scenario.get("resistance_assumptions") or {}
        lines.append("- resistance_assumptions:")
        for field in (
            "structural_conflict",
            "resource_reallocation_drag",
            "cultural_misalignment",
            "veto_node_intensity",
            "aggregate_resistance",
        ):
            if field in resistance:
                lines.append(f"  - {field}: {resistance[field]}")

        rationale = resistance.get("assumption_rationale") or []
        if rationale:
            lines.append("- assumption_rationale:")
            for item in rationale:
                lines.append(f"  - {item}")

        modeling_notes = scenario.get("modeling_notes") or []
        if modeling_notes:
            lines.append("- modeling_notes:")
            for item in modeling_notes:
                lines.append(f"  - {item}")

    lines.append("")
    return "\n".join(lines)