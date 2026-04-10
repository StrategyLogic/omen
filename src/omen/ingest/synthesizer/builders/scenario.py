"""Scenario ontology builders for deterministic planning flow."""

from __future__ import annotations

from datetime import datetime
from typing import Any


_REQUIRED_SCENARIO_KEYS: tuple[str, str, str] = ("A", "B", "C")


def _nonempty_text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _validate_structured_scenario(raw: dict[str, Any], *, scenario_key: str) -> None:
    missing_fields: list[str] = []
    for field_name in ("title", "goal", "target", "objective"):
        if not str(raw.get(field_name) or "").strip():
            missing_fields.append(field_name)

    variables = raw.get("variables")
    if not isinstance(variables, list) or not variables:
        missing_fields.append("variables")

    if not _nonempty_text_list(raw.get("constraints")):
        missing_fields.append("constraints")
    if not _nonempty_text_list(raw.get("tradeoff_pressure")):
        missing_fields.append("tradeoff_pressure")

    if missing_fields:
        raise ValueError(
            "LLM scenario decomposition produced incomplete structured payload "
            f"for slot {scenario_key}: missing {sorted(set(missing_fields))}"
        )


def normalize_scenario_ontology_scenarios(llm_scenarios: list[Any]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}

    for index, item in enumerate(llm_scenarios, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                "LLM scenario decomposition must return JSON objects for all slots "
                f"(invalid position: {index})"
            )

        key = str(item.get("scenario_key") or "").strip().upper()
        if key not in _REQUIRED_SCENARIO_KEYS:
            raise ValueError(
                f"LLM scenario decomposition has invalid scenario_key at position {index}: {key!r}"
            )
        if key in by_key:
            raise ValueError(f"LLM scenario decomposition duplicated scenario_key: {key}")
        by_key[key] = item

    missing = [key for key in _REQUIRED_SCENARIO_KEYS if key not in by_key]
    if missing:
        raise ValueError(f"LLM scenario decomposition missing required slots: {missing}")

    normalized: list[dict[str, Any]] = []
    for key in _REQUIRED_SCENARIO_KEYS:
        raw = by_key[key]
        _validate_structured_scenario(raw, scenario_key=key)

        raw_variables = raw.get("variables")
        variables: list[dict[str, Any]] = []
        if isinstance(raw_variables, list):
            for item in raw_variables:
                if isinstance(item, dict):
                    variables.append(item)

        if not variables:
            raise ValueError(f"LLM scenario decomposition slot {key} has empty variables")

        resistance_raw = raw.get("resistance_assumptions") or {}
        if not isinstance(resistance_raw, dict):
            raise ValueError(
                f"LLM scenario decomposition slot {key} must provide object resistance_assumptions"
            )

        rationale = [
            str(x).strip()
            for x in (resistance_raw.get("assumption_rationale") or [])
            if str(x).strip()
        ]
        if not rationale:
            raise ValueError(
                f"LLM scenario decomposition slot {key} missing resistance_assumptions.assumption_rationale"
            )

        normalized.append(
            {
                "scenario_key": key,
                "title": str(raw.get("title") or "").strip(),
                "goal": str(raw.get("goal") or "").strip(),
                "target": str(raw.get("target") or "").strip(),
                "objective": str(raw.get("objective") or "").strip(),
                "variables": variables,
                "constraints": _nonempty_text_list(raw.get("constraints")),
                "tradeoff_pressure": _nonempty_text_list(raw.get("tradeoff_pressure")),
                "resistance_assumptions": {
                    "structural_conflict": float(resistance_raw["structural_conflict"]),
                    "resource_reallocation_drag": float(resistance_raw["resource_reallocation_drag"]),
                    "cultural_misalignment": float(resistance_raw["cultural_misalignment"]),
                    "veto_node_intensity": float(resistance_raw["veto_node_intensity"]),
                    "aggregate_resistance": float(resistance_raw["aggregate_resistance"]),
                    "assumption_rationale": rationale,
                },
                "modeling_notes": [
                    str(x).strip()
                    for x in (raw.get("modeling_notes") or [])
                    if str(x).strip()
                ],
            }
        )
    return normalized


def build_scenario_ontology_from_decomposition(
    *,
    situation_artifact: dict[str, Any],
    llm_decomposition: dict[str, Any],
    pack_id: str,
    pack_version: str,
) -> dict[str, Any]:
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
        "planning_query_ref": str(llm_decomposition.get("planning_query_ref") or "traces/planning_query.json"),
        "prior_snapshot_ref": str(llm_decomposition.get("prior_snapshot_ref") or "traces/prior_snapshot.json"),
        "scenarios": normalize_scenario_ontology_scenarios(
            list(llm_decomposition.get("scenarios") or [])
        ),
        "decomposition_quality": llm_decomposition.get("decomposition_quality") or {},
        "source_meta": source_meta,
    }
