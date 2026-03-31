from __future__ import annotations

from omen.scenario.ontology_validator import validate_actor_ontology_payload
from omen.scenario.validator import format_validation_report


def test_actor_validator_report_pass() -> None:
    report = format_validation_report(target_artifact="output/actors/xd", errors=[])
    assert report["status"] == "pass"
    assert report["errors"] == []


def test_actor_validator_report_fail() -> None:
    report = format_validation_report(
        target_artifact="output/actors/xd/actor_ontology.json",
        errors=[{"field": "meta", "reason": "missing object"}],
    )
    assert report["status"] == "fail"
    assert len(report["errors"]) == 1


def test_actor_profile_passes_when_redacted_shape_is_valid() -> None:
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
                "name": "Actor A",
                "type": "founder",
                "profile": {
                    "mental_patterns": {"redacted": True},
                    "strategic_style": {"redacted": True},
                },
            }
        ],
        "events": [],
        "influences": {"redacted": True},
    }
    assert validate_actor_ontology_payload(payload) == []


def test_actor_profile_ignores_non_schema_extra_fields() -> None:
    payload = {
        "meta": {
            "case_id": "xd",
            "version": "v0.1.0-public",
            "disclosure_level": "public-structure",
            "strategic_dimensions": ["mental_patterns", "strategic_style"],
            "actor_relation_count": 2,
        },
        "actors": [
            {
                "id": "a1",
                "name": "Actor A",
                "type": "ceo",
                "profile": {
                    "mental_patterns": {"redacted": True},
                    "strategic_style": {"redacted": True},
                },
            },
            {"id": "a2", "name": "Stakeholder", "type": "role"},
        ],
        "events": [],
        "influences": [{"source": "a1", "target": "x", "type": "influences", "origin": "system_generated"}],
    }
    issues = validate_actor_ontology_payload(payload)
    assert issues == []
