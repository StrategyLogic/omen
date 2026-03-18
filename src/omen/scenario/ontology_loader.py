"""Load and bind case ontology input packages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.scenario.ontology_models import OntologyInputPackage
from omen.scenario.ontology_validator import (
    OntologyValidationIssue,
    OntologyValidationError,
    validate_ontology_input_or_raise,
)
from omen.scenario.validator import ScenarioConfig


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
        },
    }
