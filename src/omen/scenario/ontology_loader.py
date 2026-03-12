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
    }
