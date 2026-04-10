"""Scenario ontology builders for deterministic planning flow."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from omen.ingest.models import OntologyInputPackage
from omen.ingest.validators.actor import (
    OntologyValidationIssue,
    OntologyValidationError,
)
from omen.ingest.validators.scenario import ScenarioConfig
from omen.ingest.validators.strategy import validate_ontology_input_or_raise


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


def _extract_actor_ids(actor_items: Any) -> set[str]:
    if not isinstance(actor_items, list):
        return set()
    actor_ids: set[str] = set()
    for item in actor_items:
        if isinstance(item, str):
            value = item.strip()
            if value:
                actor_ids.add(value)
            continue
        if isinstance(item, dict):
            actor_id = str(item.get("actor_id") or item.get("id") or item.get("name") or "").strip()
            if actor_id:
                actor_ids.add(actor_id)
    return actor_ids


def _extract_adoption_resistance(market_space: Any) -> Any:
    if not isinstance(market_space, dict):
        return None

    market_attributes = market_space.get("market_attributes")
    if isinstance(market_attributes, dict) and "adoption_resistance" in market_attributes:
        return market_attributes.get("adoption_resistance")

    for key in ("attributes", "properties"):
        value = market_space.get(key)
        if isinstance(value, dict) and "adoption_resistance" in value:
            return value.get("adoption_resistance")

    constraints = market_space.get("constraints")
    if isinstance(constraints, list):
        for item in constraints:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("id") or "").strip().lower()
            if "adoption_resistance" in name:
                return item.get("value")

    return None


def _extract_market_attribute(market_space: Any, key: str) -> Any:
    if not isinstance(market_space, dict):
        return None

    market_attributes = market_space.get("market_attributes")
    if isinstance(market_attributes, dict) and key in market_attributes:
        return market_attributes.get(key)

    for bucket in ("attributes", "properties"):
        value = market_space.get(bucket)
        if isinstance(value, dict) and key in value:
            return value.get(key)

    return None


def load_ontology_input(path: str | Path) -> OntologyInputPackage:
    ontology_path = Path(path)
    payload = json.loads(ontology_path.read_text(encoding="utf-8"))
    return validate_ontology_input_or_raise(payload)


def bind_ontology_to_scenario(
    ontology: OntologyInputPackage,
    scenario: ScenarioConfig,
) -> dict[str, Any]:
    scenario_actor_ids = {actor.actor_id for actor in scenario.actors}
    ontology_actor_ids = {actor.actor_id for actor in ontology.abox.actors}

    missing_from_scenario = sorted(ontology_actor_ids - scenario_actor_ids)
    if missing_from_scenario:
        issues = [
            OntologyValidationIssue(
                code="actor_scenario_mismatch",
                message=(
                    "ontology actor_id is not present in scenario actors: "
                    f"{actor_id}"
                ),
                path="abox.actors",
            )
            for actor_id in missing_from_scenario
        ]
        raise OntologyValidationError(issues)

    tech_space = ontology.tech_space_ontology or {}
    market_space = ontology.market_space_ontology or {}
    tech_actor_ids = _extract_actor_ids(tech_space.get("actors") if isinstance(tech_space, dict) else None)
    market_actor_ids = _extract_actor_ids(
        market_space.get("actors") if isinstance(market_space, dict) else None
    )
    shared_actor_ids = set(ontology.shared_actors)

    return {
        "meta": ontology.meta.model_dump(mode="python"),
        "actor_count": len(ontology.abox.actors),
        "concept_count": len(ontology.tbox.concepts),
        "axiom_count": len(ontology.tbox.axioms),
        "applied_axioms": {
            "activation": [rule.rule_id for rule in ontology.reasoning_profile.activation_rules],
            "propagation": [rule.rule_id for rule in ontology.reasoning_profile.propagation_rules],
            "counterfactual": [
                rule.rule_id for rule in ontology.reasoning_profile.counterfactual_rules
            ],
        },
        "space_summary": {
            "tech_space_actor_count": len(tech_actor_ids),
            "market_space_actor_count": len(market_actor_ids),
            "shared_actor_count": len(shared_actor_ids),
            "shared_actor_overlap_count": len(tech_actor_ids & market_actor_ids),
            "adoption_resistance": _extract_adoption_resistance(market_space),
            "incumbent_response_speed": _extract_market_attribute(
                market_space,
                "incumbent_response_speed",
            ),
            "value_perception_gap": _extract_market_attribute(
                market_space,
                "value_perception_gap",
            ),
        },
    }
