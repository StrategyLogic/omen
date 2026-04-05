"""Build and render situation/scenario artifacts for deterministic simulation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

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


def situation_artifact_to_markdown(situation: dict[str, Any]) -> str:
    def _as_text_list(value: Any) -> list[str]:
        if isinstance(value, list):
            output: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    name = str(item.get("name") or item.get("id") or "").strip()
                    if name:
                        output.append(name)
                else:
                    text = str(item).strip()
                    if text:
                        output.append(text)
            return output
        return []

    def _append_bullets(lines: list[str], items: list[str], *, fallback: str) -> None:
        if items:
            for item in items:
                lines.append(f"- {item}")
            return
        lines.append(f"- {fallback}")

    def _dedupe_semantic(items: list[str]) -> list[str]:
        ordered = sorted((item.strip() for item in items if item.strip()), key=len, reverse=True)
        selected: list[str] = []
        for item in ordered:
            lowered = item.lower()
            if any(lowered == kept.lower() or lowered in kept.lower() for kept in selected):
                continue
            selected.append(item)

        output: list[str] = []
        lowered_selected = {item.lower() for item in selected}
        for item in items:
            text = item.strip()
            if text and text.lower() in lowered_selected and text not in output:
                output.append(text)
        return output

    lines: list[str] = []
    context = situation.get("context") or {}
    source_meta = situation.get("source_meta") or {}
    hard_constraints = _as_text_list(context.get("hard_constraints"))
    known_unknowns = _dedupe_semantic(_as_text_list(context.get("known_unknowns")))

    lines.append("# 📊 Strategic Situation Brief")
    lines.append("")
    lines.append(f"**ID:** {situation.get('id', 'unknown')}")
    lines.append(f"**Version:** {situation.get('version', '')} (Phase 1)")

    title = str(context.get("title") or "").strip()
    if title:
        lines.append(f"**Core Topic:** {title}")
    if source_meta.get("source_path"):
        lines.append(f"**Source:** {source_meta.get('source_path')}")
    if source_meta.get("generated_at"):
        lines.append(f"**Generated:** {source_meta.get('generated_at')}")

    lines.append("")
    current_state = str(context.get("current_state") or "").strip()
    core_dilemma = str(context.get("core_dilemma") or "").strip()
    core_question = str(context.get("core_question") or "").strip()
    if current_state or core_dilemma or core_question:
        summary_parts: list[str] = ["**Executive Summary:**"]
        if title:
            summary_parts.append(
                f"As this strategy review opens for {title}, the room is already under pressure: time, alignment, and strategic direction are all contested."
            )
        else:
            summary_parts.append(
                "As this strategy review opens, the room is already under pressure: time, alignment, and strategic direction are all contested."
            )
        summary_parts.append(
            "The organization is navigating a high-pressure transition and must make consequential choices before market pressure hardens into structural disadvantage."
        )
        if core_dilemma:
            summary_parts.append(f"The central dilemma is: {core_dilemma}")
        if core_question:
            summary_parts.append(f"Key strategic question: {core_question}")
        lines.append(" ".join(summary_parts))

    lines.append("")
    lines.append("---")

    lines.append("")
    lines.append("## 1. 🎭 Current State")
    if current_state:
        lines.append(current_state)
    else:
        lines.append("Current state details are not specified.")

    lines.append("")
    lines.append("## 2. 🎯 Target Outcomes")
    _append_bullets(
        lines,
        _as_text_list(context.get("target_outcomes")),
        fallback="Target outcomes are not specified.",
    )

    lines.append("")
    lines.append("## 3. ⚔️ Core Question")
    if core_question:
        lines.append(core_question)
    else:
        lines.append("Core question is not specified.")

    lines.append("")
    lines.append("## 4. ⚖️ Dilemma")
    lines.append(f"> {core_dilemma or 'Core dilemma is not specified.'}")

    lines.append("")
    lines.append("## 5. 🎯 Key Decision Point")
    key_decision_point = str(context.get("key_decision_point") or "").strip()
    lines.append(key_decision_point or "Key decision point is not specified.")

    lines.append("")
    lines.append("## 6. 🧱 Hard Constraints")
    _append_bullets(lines, hard_constraints, fallback="No hard constraints were extracted.")

    lines.append("")
    lines.append("## 7. ⚠️ Known Unknowns")
    _append_bullets(lines, known_unknowns, fallback="No known unknowns were identified.")

    lines.append("")
    lines.append("## 8. 📉 Confidence & Uncertainty")
    if known_unknowns:
        lines.append("Overall Confidence: 0.5 (medium).")
        lines.append(
            "This context captures the core strategic tension, but uncertainty remains material because key unknowns are unresolved and require targeted follow-up."
        )
    else:
        lines.append("Overall Confidence: 0.7 (medium-high).")
        lines.append("Current context appears internally consistent and does not surface explicit unresolved unknowns.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### Omen reminder")
    lines.append("")
    lines.append("This situation brief is generated by Omen LLM-based analyzer from the source document.")
    lines.append("")
    lines.append("**Status:** Phase 1 Complete (Context Extraction)")
    lines.append("**Next Step:** Run `omen scenario --situation <situation_json_path>` to generate deterministic A/B/C scenarios.")

    lines.append("")
    return "\n".join(lines)


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
