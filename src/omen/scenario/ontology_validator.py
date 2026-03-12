"""Validation entrypoints for ontology input packages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from omen.scenario.ontology_models import OntologyInputPackage
from omen.scenario.ontology_vocab import APPROVED_RELATIONS, looks_like_actor_concept


@dataclass(slots=True)
class OntologyValidationIssue:
    code: str
    message: str
    path: str


class OntologyValidationError(ValueError):
    def __init__(self, issues: list[OntologyValidationIssue]) -> None:
        self.issues = issues
        message = "ontology package validation failed: " + "; ".join(
            f"{i.path} [{i.code}] {i.message}" for i in issues
        )
        super().__init__(message)


def _check_unique(values: list[str], path: str, code: str, label: str) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    for dup in sorted(duplicates):
        issues.append(
            OntologyValidationIssue(
                code=code,
                message=f"duplicate {label}: {dup}",
                path=path,
            )
        )
    return issues


def _semantic_checks(package: OntologyInputPackage) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []

    concepts = package.tbox.concepts
    concept_names = [c.name for c in concepts]
    concept_name_set = set(concept_names)
    issues.extend(_check_unique(concept_names, "tbox.concepts", "duplicate_concept", "concept"))

    actor_concepts = [c.name for c in concepts if c.category == "actor"]
    for concept in actor_concepts:
        if not looks_like_actor_concept(concept):
            issues.append(
                OntologyValidationIssue(
                    code="actor_naming_violation",
                    message=f"actor concept should end with 'Actor': {concept}",
                    path="tbox.concepts",
                )
            )

    relation_keys: list[str] = []
    for relation in package.tbox.relations:
        relation_keys.append(f"{relation.name}:{relation.source}:{relation.target}")
        if relation.name not in APPROVED_RELATIONS:
            issues.append(
                OntologyValidationIssue(
                    code="invalid_relation_name",
                    message=f"relation name '{relation.name}' is not in approved semantic vocabulary",
                    path="tbox.relations",
                )
            )
        if relation.source not in concept_name_set:
            issues.append(
                OntologyValidationIssue(
                    code="unknown_relation_source",
                    message=f"relation source '{relation.source}' is not a declared concept",
                    path="tbox.relations",
                )
            )
        if relation.target not in concept_name_set:
            issues.append(
                OntologyValidationIssue(
                    code="unknown_relation_target",
                    message=f"relation target '{relation.target}' is not a declared concept",
                    path="tbox.relations",
                )
            )
    issues.extend(
        _check_unique(
            relation_keys,
            "tbox.relations",
            "duplicate_relation",
            "relation tuple",
        )
    )

    axiom_ids = [a.id for a in package.tbox.axioms]
    issues.extend(_check_unique(axiom_ids, "tbox.axioms", "duplicate_axiom_id", "axiom id"))
    axiom_id_set = set(axiom_ids)

    for group_name, refs in (
        ("activation_rules", package.reasoning_profile.activation_rules),
        ("propagation_rules", package.reasoning_profile.propagation_rules),
        ("counterfactual_rules", package.reasoning_profile.counterfactual_rules),
    ):
        for ref in refs:
            if ref.rule_id not in axiom_id_set:
                issues.append(
                    OntologyValidationIssue(
                        code="unresolved_rule_ref",
                        message=f"rule ref '{ref.rule_id}' is not declared in tbox.axioms",
                        path=f"reasoning_profile.{group_name}",
                    )
                )

    actor_ids = [a.actor_id for a in package.abox.actors]
    issues.extend(_check_unique(actor_ids, "abox.actors", "duplicate_actor_id", "actor id"))
    actor_id_set = set(actor_ids)

    capability_names = {c.name for c in concepts if c.category == "capability"}
    mapped_actor_ids: set[str] = set()
    for cap in package.abox.capabilities:
        mapped_actor_ids.add(cap.actor_id)
        if cap.actor_id not in actor_id_set:
            issues.append(
                OntologyValidationIssue(
                    code="unknown_capability_actor",
                    message=f"capability actor_id '{cap.actor_id}' is not declared in abox.actors",
                    path="abox.capabilities",
                )
            )
        if capability_names and cap.name not in capability_names:
            issues.append(
                OntologyValidationIssue(
                    code="unknown_capability_name",
                    message=f"capability name '{cap.name}' is not declared as capability concept",
                    path="abox.capabilities",
                )
            )

    for actor_id in sorted(actor_id_set - mapped_actor_ids):
        issues.append(
            OntologyValidationIssue(
                code="actor_without_capability",
                message=f"actor '{actor_id}' has no capability mapping",
                path="abox.capabilities",
            )
        )

    constraint_names = [c.name for c in package.abox.constraints]
    issues.extend(
        _check_unique(
            constraint_names,
            "abox.constraints",
            "duplicate_constraint_name",
            "constraint name",
        )
    )

    return issues


def validate_ontology_input(payload: dict[str, Any]) -> OntologyInputPackage:
    try:
        package = OntologyInputPackage.model_validate(payload)
    except ValidationError as exc:
        issues = [
            OntologyValidationIssue(
                code="schema_validation_error",
                message=err.get("msg", "invalid value"),
                path=".".join(str(p) for p in err.get("loc", ())),
            )
            for err in exc.errors()
        ]
        raise OntologyValidationError(issues) from exc

    issues = _semantic_checks(package)
    if issues:
        raise OntologyValidationError(issues)
    return package


def validate_ontology_input_or_raise(payload: dict[str, Any]) -> OntologyInputPackage:
    return validate_ontology_input(payload)
