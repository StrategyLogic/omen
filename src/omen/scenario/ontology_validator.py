"""Validation entrypoints for ontology input packages."""

# pylint: disable=too-many-lines

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
import warnings

from pydantic import ValidationError

from omen.ingest.synthesizer.schema import BACKGROUND_FACT_FIELDS, VERSION
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


def _is_strategic_actor_type(value: Any) -> bool:
    actor_type = str(value or "").strip().lower()
    return actor_type == "strategicactor"


def _is_version_compatible(value: Any) -> bool:
    return str(value or "").strip() == VERSION


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def validate_actor_ontology_payload(payload: dict[str, Any]) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        issues.append(OntologyValidationIssue(code="missing_meta", message="meta must be an object", path="meta"))
        return issues

    if not _is_version_compatible(meta.get("version")):
        issues.append(
            OntologyValidationIssue(
                code="invalid_version",
                message=f"meta.version must equal '{VERSION}'",
                path="meta.version",
            )
        )

    actors = payload.get("actors")
    if not isinstance(actors, list):
        issues.append(OntologyValidationIssue(code="missing_actors", message="actors must be an array", path="actors"))
    else:
        strategic_actor_count = 0
        for idx, actor in enumerate(actors):
            base = f"actors[{idx}]"
            if not isinstance(actor, dict):
                continue
            for required in ("id", "name", "type"):
                if required not in actor:
                    issues.append(
                        OntologyValidationIssue(
                            code="missing_actor_field",
                            message=f"{required} is required in actor schema",
                            path=f"{base}.{required}",
                        )
                    )

            if not _is_strategic_actor_type(actor.get("type")):
                continue

            strategic_actor_count += 1
            profile = actor.get("profile")
            if not isinstance(profile, dict):
                issues.append(
                    OntologyValidationIssue(
                        code="missing_actor_field",
                        message="profile is required for strategic actor types",
                        path=f"{base}.profile",
                    )
                )
                continue

            background_facts = profile.get("background_facts")
            if not isinstance(background_facts, dict):
                issues.append(
                    OntologyValidationIssue(
                        code="invalid_background_facts",
                        message="profile.background_facts must be an object",
                        path=f"{base}.profile.background_facts",
                    )
                )
                continue

            for field in BACKGROUND_FACT_FIELDS:
                if field not in background_facts:
                    issues.append(
                        OntologyValidationIssue(
                            code="missing_background_fact_field",
                            message=f"profile.background_facts.{field} is required",
                            path=f"{base}.profile.background_facts.{field}",
                        )
                    )

            extra_fields = sorted(set(background_facts.keys()) - set(BACKGROUND_FACT_FIELDS))
            for field in extra_fields:
                issues.append(
                    OntologyValidationIssue(
                        code="unexpected_background_fact_field",
                        message=f"profile.background_facts.{field} is not allowed",
                        path=f"{base}.profile.background_facts.{field}",
                    )
                )

            birth_year = background_facts.get("birth_year")
            if birth_year is not None and not isinstance(birth_year, int):
                issues.append(
                    OntologyValidationIssue(
                        code="invalid_background_fact_type",
                        message="profile.background_facts.birth_year must be integer or null",
                        path=f"{base}.profile.background_facts.birth_year",
                    )
                )

            origin = background_facts.get("origin")
            if origin is not None and not isinstance(origin, str):
                issues.append(
                    OntologyValidationIssue(
                        code="invalid_background_fact_type",
                        message="profile.background_facts.origin must be string or null",
                        path=f"{base}.profile.background_facts.origin",
                    )
                )

            for list_field in ("education", "career_trajectory", "key_experiences"):
                if not _is_str_list(background_facts.get(list_field)):
                    issues.append(
                        OntologyValidationIssue(
                            code="invalid_background_fact_type",
                            message=f"profile.background_facts.{list_field} must be string[]",
                            path=f"{base}.profile.background_facts.{list_field}",
                        )
                    )

        if strategic_actor_count == 0:
            issues.append(
                OntologyValidationIssue(
                    code="missing_strategic_actor",
                    message="at least one strategic actor (type=StrategicActor) is required",
                    path="actors",
                )
            )

    events = payload.get("events")
    if not isinstance(events, list):
        issues.append(OntologyValidationIssue(code="missing_events", message="events must be an array", path="events"))
    return issues


def validate_actor_strategy_link_payload(payload: dict[str, Any], *, expected_actor_filename: str) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    actor_ref = payload.get("actor_ref")
    if not isinstance(actor_ref, dict):
        issues.append(
            OntologyValidationIssue(
                code="missing_actor_ref",
                message="strategy ontology must include actor_ref",
                path="actor_ref",
            )
        )
        return issues

    path_value = str(actor_ref.get("path") or "").strip()
    if path_value != expected_actor_filename:
        issues.append(
            OntologyValidationIssue(
                code="invalid_actor_ref_path",
                message=f"actor_ref.path must equal {expected_actor_filename}",
                path="actor_ref.path",
            )
        )
    return issues


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _infer_strategy_name(meta: dict[str, Any]) -> str:
    explicit = str(meta.get("strategy") or "").strip()
    if explicit:
        slug = _slugify(explicit)
        if slug:
            return slug

    haystack = " ".join(
        str(meta.get(key) or "") for key in ("domain", "case_title", "case_id")
    ).lower()
    strategy_hints = (
        ("x developer", "new_tech_market_entry"),
        ("x-developer", "new_tech_market_entry"),
        ("market expansion", "new_tech_market_entry"),
        ("new tech", "new_tech_market_entry"),
        ("database-vs-ai-memory", "database_paradigm_competition"),
        ("database vs ai memory", "database_paradigm_competition"),
        ("database paradigm", "database_paradigm_competition"),
        ("ontology-battlefield", "database_paradigm_competition"),
    )
    for token, strategy in strategy_hints:
        if token in haystack:
            return strategy

    fallback = _slugify(str(meta.get("domain") or meta.get("case_id") or ""))
    return fallback or "case_specific_strategy"


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

    def _normalize_actor_kind_and_role(raw_type: str, raw_role: str) -> tuple[str, str]:
        token = str(raw_type or "").strip()
        lowered = token.lower()
        role = str(raw_role or "").strip()

        if token in {"Actor", "StrategicActor"}:
            if token == "StrategicActor":
                return token, role or "strategic_actor"
            return token, role or "actor"

        strategic_role_tokens = {"founder", "ceo", "top_management", "top management"}
        if lowered in strategic_role_tokens:
            return "StrategicActor", role or lowered.replace(" ", "_")

        if lowered.endswith("actor") and lowered not in {"actor", "strategicactor"}:
            return "Actor", role or lowered.removesuffix("actor") or "actor"

        return "Actor", role or (lowered if lowered else "actor")

    def _append_actor(actor: dict[str, Any]) -> None:
        actor_id = str(
            actor.get("actor_id") or actor.get("id") or _slugify(str(actor.get("name") or ""))
        ).strip()
        if not actor_id:
            return
        actor_type, role = _normalize_actor_kind_and_role(
            str(actor.get("actor_type") or actor.get("concept") or "Actor"),
            str(actor.get("role") or actor.get("name") or ""),
        )
        profile = actor.get("profile") if isinstance(actor.get("profile"), dict) else None
        if actor_type == "StrategicActor" and profile is None:
            profile = {
                "mental_patterns": {},
                "strategic_style": {},
            }
        normalized.append(
            {
                "actor_id": actor_id,
                "actor_type": actor_type,
                "role": role,
                "shared_id": str(actor.get("shared_id") or "").strip() or None,
                "labels": list(actor.get("labels") or []),
                "profile": profile,
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


def _ensure_actor_hierarchy_tbox(tbox: dict[str, Any]) -> None:
    concepts = [item for item in list(tbox.get("concepts") or []) if isinstance(item, dict)]
    concept_by_name = {str(item.get("name") or "").strip(): item for item in concepts}

    if "Actor" not in concept_by_name:
        concepts.append(
            {
                "name": "Actor",
                "description": "Top-level action subject type.",
                "category": "actor",
            }
        )
    if "StrategicActor" not in concept_by_name:
        concepts.append(
            {
                "name": "StrategicActor",
                "description": "Actor subclass carrying strategic profile fields.",
                "category": "actor",
            }
        )
    tbox["concepts"] = concepts

    relations = [item for item in list(tbox.get("relations") or []) if isinstance(item, dict)]
    has_inheritance = any(
        str(rel.get("name") or "").strip() == "inherits_from"
        and str(rel.get("source") or "").strip() == "StrategicActor"
        and str(rel.get("target") or "").strip() == "Actor"
        for rel in relations
    )
    if not has_inheritance:
        relations.append(
            {
                "name": "inherits_from",
                "source": "StrategicActor",
                "target": "Actor",
                "description": "StrategicActor is a subtype of Actor.",
            }
        )
    tbox["relations"] = relations


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


def _normalize_events(events: list[Any]) -> tuple[list[dict[str, Any]], list[str]]:
    normalized: list[dict[str, Any]] = []
    warnings_list: list[str] = []

    for item in events:
        if not isinstance(item, dict):
            continue

        # Already normalized shape
        if "event_type" in item and isinstance(item.get("payload"), dict):
            event_type = str(item.get("event_type") or "").strip()
            payload = dict(item.get("payload") or {})
            target = item.get("target")
            normalized.append(
                {
                    "event_type": event_type or "event",
                    "target": str(target).strip() if isinstance(target, str) and target.strip() else None,
                    "payload": payload,
                }
            )
            continue

        # Legacy shape compatibility: event/event_id/id/description/time/... -> event_type + payload
        event_type = str(item.get("event") or item.get("type") or item.get("event_type") or "event").strip()
        target = str(item.get("target") or item.get("event_id") or item.get("id") or "").strip() or None
        payload = dict(item)

        if target and "event_id" not in payload:
            payload["event_id"] = target

        normalized.append(
            {
                "event_type": event_type or "event",
                "target": target,
                "payload": payload,
            }
        )
        warnings_list.append(
            "Auto-fix: normalized legacy abox.events item to event_type/payload schema."
        )

    return normalized, warnings_list


def _align_abox_entries(
    *,
    capabilities: list[Any],
    constraints: list[Any],
    capability_concepts: set[str],
    constraint_concepts: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    warnings_list: list[str] = []

    normalized_capabilities: list[dict[str, Any]] = []
    normalized_constraints: list[dict[str, Any]] = [item for item in constraints if isinstance(item, dict)]
    existing_constraint_names = {
        str(item.get("name") or "").strip() for item in normalized_constraints if isinstance(item, dict)
    }

    for cap in capabilities:
        if not isinstance(cap, dict):
            continue
        name = str(cap.get("name") or "").strip()
        if not name:
            continue

        if name in constraint_concepts and name not in capability_concepts:
            value = cap.get("score", cap.get("value", 1.0))
            if name not in existing_constraint_names:
                normalized_constraints.append({"name": name, "value": value})
                existing_constraint_names.add(name)
            warnings_list.append(
                "Auto-fix: moved abox.capabilities item "
                f"'{name}' to abox.constraints to align with tbox concept category 'constraint'."
            )
            continue

        normalized_capabilities.append(cap)

    existing_capability_keys = {
        (
            str(item.get("actor_id") or "").strip(),
            str(item.get("name") or "").strip(),
        )
        for item in normalized_capabilities
        if isinstance(item, dict)
    }

    final_constraints: list[dict[str, Any]] = []
    for constraint in normalized_constraints:
        name = str(constraint.get("name") or "").strip()
        if not name:
            continue

        if name in capability_concepts and name not in constraint_concepts:
            actor_id = str(constraint.get("actor_id") or "system").strip() or "system"
            value = constraint.get("value")
            if value is None:
                score = 0.5
            else:
                try:
                    score = float(value)
                except (TypeError, ValueError):
                    score = 0.5
            score = max(0.0, min(1.0, score))
            key = (actor_id, name)
            if key not in existing_capability_keys:
                normalized_capabilities.append({"actor_id": actor_id, "name": name, "score": score})
                existing_capability_keys.add(key)
            warnings_list.append(
                "Auto-fix: moved abox.constraints item "
                f"'{name}' to abox.capabilities to align with tbox concept category 'capability'."
            )
            continue

        final_constraints.append(constraint)

    return normalized_capabilities, final_constraints, warnings_list


def _normalize_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    normalized = dict(payload)
    normalization_warnings: list[str] = []

    meta = dict(payload.get("meta") or {})
    meta.setdefault("version", meta.get("ontology_version") or "1.0")
    meta.setdefault("domain", meta.get("case_title") or "case-domain")
    meta["strategy"] = _infer_strategy_name(meta)
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

    strategic_indexes = [idx for idx, actor in enumerate(abox["actors"]) if actor.get("actor_type") == "StrategicActor"]
    if not strategic_indexes and abox["actors"]:
        first = dict(abox["actors"][0])
        first["actor_type"] = "StrategicActor"
        if not isinstance(first.get("profile"), dict):
            first["profile"] = {"mental_patterns": {}, "strategic_style": {}}
        abox["actors"][0] = first
    elif len(strategic_indexes) > 1:
        for idx in strategic_indexes[1:]:
            actor = dict(abox["actors"][idx])
            actor["actor_type"] = "Actor"
            actor.pop("profile", None)
            abox["actors"][idx] = actor

    _ensure_actor_hierarchy_tbox(tbox)
    normalized_events, event_warnings = _normalize_events(list(abox.get("events") or []))
    abox["events"] = normalized_events
    normalization_warnings.extend(event_warnings)
    raw_capabilities = list(abox.get("capabilities") or [])
    raw_constraints = list(abox.get("constraints") or [])
    capability_concepts = {
        str(concept.get("name") or "")
        for concept in tbox["concepts"]
        if concept.get("category") == "capability"
    }
    constraint_concepts = {
        str(concept.get("name") or "")
        for concept in tbox["concepts"]
        if concept.get("category") == "constraint"
    }
    aligned_capabilities, aligned_constraints, warnings_list = _align_abox_entries(
        capabilities=raw_capabilities,
        constraints=raw_constraints,
        capability_concepts=capability_concepts,
        constraint_concepts=constraint_concepts,
    )
    abox["capabilities"] = aligned_capabilities
    abox["constraints"] = aligned_constraints
    normalization_warnings.extend(warnings_list)
    tbox["relations"] = _normalize_relations(
        list(tbox.get("relations") or []),
        abox["actors"],
        tbox["concepts"],
    )
    normalized["tbox"] = tbox
    normalized["abox"] = abox

    normalized["reasoning_profile"] = reasoning_profile

    if isinstance(payload.get("tech_space_ontology"), dict):
        normalized["tech_space_ontology"] = dict(payload["tech_space_ontology"])
    if isinstance(payload.get("market_space_ontology"), dict):
        normalized["market_space_ontology"] = dict(payload["market_space_ontology"])
    if isinstance(payload.get("shared_actors"), list):
        normalized["shared_actors"] = list(payload["shared_actors"])
    return normalized, normalization_warnings


def normalize_ontology_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    return _normalize_payload(payload)


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


def _has_adoption_resistance_attribute(market_space: dict[str, Any]) -> bool:
    for key in ("market_attributes", "attributes", "properties"):
        value = market_space.get(key)
        if isinstance(value, dict) and "adoption_resistance" in value:
            return True

    constraints = market_space.get("constraints")
    if isinstance(constraints, list):
        for item in constraints:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("id") or "").strip().lower()
            if "adoption_resistance" in name:
                return True
    return False


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


def _semantic_checks(
    package: OntologyInputPackage,
    normalized_payload: dict[str, Any],
) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []

    concepts = package.tbox.concepts
    concept_names = [c.name for c in concepts]
    concept_name_set = set(concept_names)
    issues.extend(_check_unique(concept_names, "tbox.concepts", "duplicate_concept", "concept"))

    actor_concepts = [c.name for c in concepts if c.category == "actor"]
    required_actor_concepts = {"Actor", "StrategicActor"}
    missing_actor_concepts = sorted(required_actor_concepts - set(actor_concepts))
    for concept in missing_actor_concepts:
        issues.append(
            OntologyValidationIssue(
                code="missing_actor_hierarchy_concept",
                message=f"required actor concept missing: {concept}",
                path="tbox.concepts",
            )
        )

    has_actor_inheritance = any(
        rel.name == "inherits_from" and rel.source == "StrategicActor" and rel.target == "Actor"
        for rel in package.tbox.relations
    )
    if not has_actor_inheritance:
        issues.append(
            OntologyValidationIssue(
                code="missing_actor_inheritance_relation",
                message="tbox.relations must include inherits_from(StrategicActor -> Actor)",
                path="tbox.relations",
            )
        )

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

    strategic_actor_count = sum(1 for actor in package.abox.actors if actor.actor_type == "StrategicActor")
    if strategic_actor_count != 1:
        issues.append(
            OntologyValidationIssue(
                code="strategic_actor_count_mismatch",
                message="abox.actors must contain exactly one StrategicActor",
                path="abox.actors",
            )
        )

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

    tech_space = normalized_payload.get("tech_space_ontology")
    market_space = normalized_payload.get("market_space_ontology")
    shared_actors_raw = normalized_payload.get("shared_actors")

    tech_actor_ids = _extract_actor_ids(tech_space.get("actors") if isinstance(tech_space, dict) else None)
    market_actor_ids = _extract_actor_ids(
        market_space.get("actors") if isinstance(market_space, dict) else None
    )
    shared_actor_ids = _extract_actor_ids(shared_actors_raw)

    if isinstance(market_space, dict) and not _has_adoption_resistance_attribute(market_space):
        issues.append(
            OntologyValidationIssue(
                code="missing_market_adoption_resistance",
                message="market_space_ontology must declare adoption_resistance attribute or constraint",
                path="market_space_ontology",
            )
        )

    if isinstance(tech_space, dict) and isinstance(market_space, dict):
        shared_between_spaces = tech_actor_ids & market_actor_ids
        if not shared_between_spaces:
            issues.append(
                OntologyValidationIssue(
                    code="dual_space_actor_disconnected",
                    message="tech_space_ontology and market_space_ontology share no actor ids",
                    path="shared_actors",
                )
            )

    if shared_actor_ids:
        unknown_in_abox = sorted(shared_actor_ids - actor_id_set)
        for actor_id in unknown_in_abox:
            issues.append(
                OntologyValidationIssue(
                    code="shared_actor_not_in_abox",
                    message=f"shared actor '{actor_id}' is not declared in abox.actors",
                    path="shared_actors",
                )
            )

        if isinstance(tech_space, dict):
            unknown_in_tech = sorted(shared_actor_ids - tech_actor_ids)
            for actor_id in unknown_in_tech:
                issues.append(
                    OntologyValidationIssue(
                        code="shared_actor_not_in_tech_space",
                        message=f"shared actor '{actor_id}' is not declared in tech_space_ontology.actors",
                        path="shared_actors",
                    )
                )

        if isinstance(market_space, dict):
            unknown_in_market = sorted(shared_actor_ids - market_actor_ids)
            for actor_id in unknown_in_market:
                issues.append(
                    OntologyValidationIssue(
                        code="shared_actor_not_in_market_space",
                        message=f"shared actor '{actor_id}' is not declared in market_space_ontology.actors",
                        path="shared_actors",
                    )
                )

    return issues


def validate_ontology_input_with_warnings(
    payload: dict[str, Any],
) -> tuple[OntologyInputPackage, list[str]]:
    normalized_payload, normalization_warnings = normalize_ontology_payload(payload)
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

    issues = _semantic_checks(package, normalized_payload)
    if issues:
        raise OntologyValidationError(issues)
    return package, normalization_warnings


def validate_ontology_input(payload: dict[str, Any]) -> OntologyInputPackage:
    package, normalization_warnings = validate_ontology_input_with_warnings(payload)

    for message in normalization_warnings:
        warnings.warn(message, UserWarning, stacklevel=2)

    return package


def validate_ontology_input_or_raise(payload: dict[str, Any]) -> OntologyInputPackage:
    return validate_ontology_input(payload)
