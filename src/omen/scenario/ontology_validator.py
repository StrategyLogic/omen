"""Validation entrypoints for ontology input packages."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from pydantic import ValidationError

from omen.scenario.ontology_models import OntologyInputPackage
from omen.scenario.ontology_vocab import looks_like_actor_concept


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


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _infer_concept_category(name: str, declared_key: str | None = None) -> str:
    if declared_key and declared_key in {
        "actor",
        "capability",
        "constraint",
        "event",
        "outcome",
        "game",
        "other",
    }:
        return declared_key
    if name.endswith("Actor"):
        return "actor"
    lowered = name.lower()
    if any(token in lowered for token in ("capability", "ability", "skill")):
        return "capability"
    if any(token in lowered for token in ("constraint", "limit", "threshold")):
        return "constraint"
    return "other"


def _normalize_concepts(concepts: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in concepts:
        if isinstance(item, str):
            name = item.strip()
            if not name:
                continue
            normalized.append(
                {
                    "name": name,
                    "description": name,
                    "category": _infer_concept_category(name),
                }
            )
            continue

        if isinstance(item, dict) and "name" in item:
            name = str(item["name"]).strip()
            if not name:
                continue
            normalized.append(
                {
                    "name": name,
                    "description": str(item.get("description") or name),
                    "category": _infer_concept_category(name, item.get("category")),
                }
            )
            continue

        if not isinstance(item, dict):
            continue

        for node_name, node_values in item.items():
            if not isinstance(node_values, list):
                continue
            for child in node_values:
                if not isinstance(child, dict):
                    continue
                child_name = str(child.get("name") or child.get("id") or "").strip()
                if not child_name:
                    continue
                normalized.append(
                    {
                        "name": child_name,
                        "description": str(child.get("description") or child_name),
                        "category": _infer_concept_category(
                            child_name,
                            None if node_name == "concept" else node_name,
                        ),
                    }
                )
    return normalized


def _normalize_relations(
    relations: list[Any],
    actors: list[dict[str, Any]],
    concepts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    actor_type_by_id = {a.get("actor_id"): a.get("actor_type") for a in actors}
    actor_concepts = [str(c.get("name")) for c in concepts if c.get("category") == "actor"]
    capability_concepts = [str(c.get("name")) for c in concepts if c.get("category") == "capability"]
    default_source = actor_concepts[0] if actor_concepts else "Actor"
    default_target = capability_concepts[0] if capability_concepts else default_source

    for relation in relations:
        if isinstance(relation, dict) and {"name", "source", "target"}.issubset(relation):
            name = str(relation.get("name") or "").strip()
            source = str(relation.get("source") or "").strip()
            target = str(relation.get("target") or "").strip()
            if name and source and target:
                normalized.append(
                    {
                        "name": name,
                        "source": source,
                        "target": target,
                        "description": str(relation.get("description") or f"{source} {name} {target}"),
                    }
                )
            continue

        if isinstance(relation, dict) and {"relation", "from", "to"}.issubset(relation):
            name = str(relation.get("relation") or "").strip()
            source_actor_id = str(relation.get("from") or "").strip()
            target_actor_id = str(relation.get("to") or "").strip()
            source = str(actor_type_by_id.get(source_actor_id) or "").strip()
            target = str(actor_type_by_id.get(target_actor_id) or "").strip()
            if name and source and target:
                normalized.append(
                    {
                        "name": name,
                        "source": source,
                        "target": target,
                        "description": str(relation.get("description") or f"{source} {name} {target}"),
                    }
                )
            continue

        if isinstance(relation, str):
            name = relation.strip()
            if name:
                normalized.append(
                    {
                        "name": name,
                        "source": default_source,
                        "target": default_target,
                        "description": f"generic relation {name}",
                    }
                )

    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in normalized:
        key = f"{item['name']}:{item['source']}:{item['target']}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _normalize_actors(actors: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    def _append_actor(actor: dict[str, Any]) -> None:
        actor_id = str(
            actor.get("actor_id") or actor.get("id") or _slugify(str(actor.get("name") or ""))
        ).strip()
        if not actor_id:
            return
        actor_type = str(actor.get("actor_type") or actor.get("concept") or "actor").strip()
        normalized.append(
            {
                "actor_id": actor_id,
                "actor_type": actor_type,
                "labels": list(actor.get("labels") or []),
            }
        )

    for item in actors:
        if isinstance(item, dict) and "actor_id" in item:
            _append_actor(item)
            continue
        if not isinstance(item, dict):
            continue
        for node_name, node_values in item.items():
            if node_name != "actor" or not isinstance(node_values, list):
                continue
            for child in node_values:
                if isinstance(child, dict):
                    _append_actor(child)

    return normalized


def _normalize_reasoning_profile(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "activation_rules": [],
            "propagation_rules": [],
            "counterfactual_rules": [],
        }

    def _normalize_rule_refs(refs: Any) -> list[dict[str, Any]]:
        if not isinstance(refs, list):
            return []
        normalized_refs: list[dict[str, Any]] = []
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            rule_id = str(ref.get("rule_id") or ref.get("id") or ref.get("axiom_id") or "").strip()
            if not rule_id:
                continue
            normalized_refs.append({"rule_id": rule_id, "description": ref.get("description")})
        return normalized_refs

    activation_rules = _normalize_rule_refs(value.get("activation_rules"))
    propagation_rules = _normalize_rule_refs(value.get("propagation_rules"))
    counterfactual_rules = _normalize_rule_refs(value.get("counterfactual_rules"))

    if not activation_rules and not propagation_rules and not counterfactual_rules:
        fallback_rules = _normalize_rule_refs(value.get("rules"))
        activation_rules = fallback_rules

    return {
        "activation_rules": activation_rules,
        "propagation_rules": propagation_rules,
        "counterfactual_rules": counterfactual_rules,
    }


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)

    meta = dict(payload.get("meta") or {})
    meta.setdefault("version", meta.get("ontology_version") or "1.0")
    meta.setdefault("domain", meta.get("case_title") or "case-domain")
    normalized["meta"] = meta

    tbox = dict(payload.get("tbox") or {})
    tbox["concepts"] = _normalize_concepts(list(tbox.get("concepts") or []))

    axioms = list(tbox.get("axioms") or [])
    reasoning_profile = _normalize_reasoning_profile(payload.get("reasoning_profile"))
    axiom_type_by_rule_id: dict[str, str] = {}
    for group_name, axiom_type in (
        ("activation_rules", "activation"),
        ("propagation_rules", "propagation"),
        ("counterfactual_rules", "counterfactual"),
    ):
        for ref in reasoning_profile[group_name]:
            axiom_type_by_rule_id[ref["rule_id"]] = axiom_type

    normalized_axioms: list[dict[str, Any]] = []
    for axiom in axioms:
        if not isinstance(axiom, dict):
            continue
        axiom_id = str(axiom.get("id") or "").strip()
        if not axiom_id:
            continue
        resolved_type = str(axiom.get("type") or axiom_type_by_rule_id.get(axiom_id) or "custom").strip()
        statement = axiom.get("statement")
        if statement is None and resolved_type not in {"activation", "propagation", "counterfactual"}:
            statement = f"custom axiom: {axiom_id}"
        normalized_axioms.append(
            {
                "id": axiom_id,
                "type": resolved_type,
                "statement": statement,
            }
        )
    tbox["axioms"] = normalized_axioms

    abox = dict(payload.get("abox") or {})
    abox["actors"] = _normalize_actors(list(abox.get("actors") or []))
    abox["capabilities"] = list(abox.get("capabilities") or [])
    abox["constraints"] = list(abox.get("constraints") or [])
    tbox["relations"] = _normalize_relations(
        list(tbox.get("relations") or []),
        abox["actors"],
        tbox["concepts"],
    )
    normalized["tbox"] = tbox
    normalized["abox"] = abox

    normalized["reasoning_profile"] = reasoning_profile
    return normalized


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

    reasoning_profile = package.reasoning_profile
    for group_name, refs in (
        ("activation_rules", reasoning_profile.activation_rules),
        ("propagation_rules", reasoning_profile.propagation_rules),
        ("counterfactual_rules", reasoning_profile.counterfactual_rules),
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
    normalized_payload = _normalize_payload(payload)
    try:
        package = OntologyInputPackage.model_validate(normalized_payload)
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
