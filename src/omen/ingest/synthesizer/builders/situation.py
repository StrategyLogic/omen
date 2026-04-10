"""Build and render situation/scenario artifacts for deterministic simulation."""

from __future__ import annotations

from pathlib import Path
from omen.scenario.ingest_validator import DeferredScopeFeatureError


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