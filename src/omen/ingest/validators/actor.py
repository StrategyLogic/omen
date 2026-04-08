"""Actor ontology validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from omen.ingest.synthesizer.schema import BACKGROUND_FACT_FIELDS, VERSION


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
