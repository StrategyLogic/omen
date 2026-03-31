from __future__ import annotations

from omen.scenario.ontology_validator import (
    validate_actor_ontology_payload,
    validate_actor_strategy_link_payload,
)


def test_actor_schema_errors_include_field_paths() -> None:
    issues = validate_actor_ontology_payload({"meta": {}, "actors": "bad", "events": "bad"})
    paths = {issue.path for issue in issues}
    assert "actors" in paths
    assert "events" in paths


def test_strategy_actor_ref_path_must_match_actor_filename() -> None:
    issues = validate_actor_strategy_link_payload(
        {"actor_ref": {"path": "legacy_actor_slice.json"}},
        expected_actor_filename="actor_ontology.json",
    )
    assert any(issue.path == "actor_ref.path" for issue in issues)


def test_actor_schema_requires_metadata_suffix() -> None:
    payload = {
        "meta": {
            "case_id": "xd",
            "version": "v0.1.0",
            "disclosure_level": "public-structure",
            "strategic_dimensions": ["mental_patterns", "strategic_style"],
        },
        "actors": [
            {
                "id": "a1",
                "name": "A",
                "type": "founder",
                "profile": {
                    "mental_patterns": {"redacted": True},
                    "strategic_style": {"redacted": True},
                },
            }
        ],
        "events": [],
    }
    issues = validate_actor_ontology_payload(payload)
    assert any(issue.path == "meta.version" for issue in issues)


def test_schema_validator_ignores_extra_fields_like_origin() -> None:
    payload = {
        "meta": {
            "case_id": "xd",
            "version": "v0.1.0-public",
            "disclosure_level": "public-structure",
            "strategic_dimensions": ["mental_patterns", "strategic_style"],
        },
        "actors": [
            {
                "id": "a1",
                "name": "A",
                "type": "founder",
                "profile": {
                    "mental_patterns": {"redacted": True},
                    "strategic_style": {"redacted": True},
                },
            }
        ],
        "events": [],
        "influences": [{"source": "a", "target": "b", "type": "influences", "origin": "system_generated"}],
    }
    issues = validate_actor_ontology_payload(payload)
    assert issues == []


def test_schema_validator_ignores_closed_subdimension_content() -> None:
    payload = {
        "meta": {
            "case_id": "xd",
            "version": "v0.1.0-public",
            "disclosure_level": "public-structure",
            "strategic_dimensions": ["mental_patterns", "strategic_style"],
        },
        "actors": [
            {
                "id": "a1",
                "name": "A",
                "type": "founder",
                "profile": {
                    "mental_patterns": {"core_beliefs": ["x"]},
                    "strategic_style": {"redacted": True},
                },
            }
        ],
        "events": [],
    }
    issues = validate_actor_ontology_payload(payload)
    assert issues == []


def test_schema_validator_requires_profile_for_strategic_actor() -> None:
    payload = {
        "meta": {
            "case_id": "xd",
            "version": "v0.1.0-public",
            "disclosure_level": "public-structure",
            "strategic_dimensions": ["mental_patterns", "strategic_style"],
        },
        "actors": [{"id": "a1", "name": "Leader", "type": "founder"}],
        "events": [],
    }
    issues = validate_actor_ontology_payload(payload)
    assert any(issue.path == "actors[0].profile" for issue in issues)


def test_schema_validator_allows_role_actor_without_profile() -> None:
    payload = {
        "meta": {
            "case_id": "xd",
            "version": "v0.1.0-public",
            "disclosure_level": "public-structure",
            "strategic_dimensions": ["mental_patterns", "strategic_style"],
        },
        "actors": [
            {
                "id": "a1",
                "name": "Leader",
                "type": "founder",
                "profile": {
                    "mental_patterns": {"redacted": True},
                    "strategic_style": {"redacted": True},
                },
            },
            {"id": "a2", "name": "Analyst", "type": "role"},
        ],
        "events": [],
    }
    issues = validate_actor_ontology_payload(payload)
    assert issues == []
