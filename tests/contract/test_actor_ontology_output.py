from __future__ import annotations
from omen.scenario.ontology_validator import validate_actor_ontology_payload


def test_actor_ontology_contract_minimal_shape() -> None:
    payload = {
        "meta": {"case_id": "xd", "version": "1.0.0"},
        "actors": [{"id": "a1", "shared_id": "a1"}],
        "events": [{"id": "e1", "event": "launch", "time": "2016"}],
        "influences": [],
        "query_skeleton": {"query_types": ["status", "persona"]},
    }

    assert isinstance(payload["meta"], dict)
    assert isinstance(payload["actors"], list)
    assert isinstance(payload["events"], list)
    assert payload["meta"]["case_id"] == "xd"


def test_actor_ontology_public_schema_allows_extra_fields() -> None:
    payload = {
        "meta": {
            "case_id": "xd",
            "version": "v0.1.0-public",
            "disclosure_level": "public-structure",
            "strategic_dimensions": ["mental_patterns", "strategic_style"],
            "extra": "ignored",
        },
        "actors": [
            {
                "id": "a1",
                "name": "Actor A",
                "type": "founder",
                "profile": {
                    "mental_patterns": {"redacted": True},
                    "strategic_style": {"redacted": True},
                    "custom_impl": {"ok": True},
                },
                "custom_field": "ignored",
            }
        ],
        "events": [{"id": "e1"}],
        "influences": [{"origin": "semantic_enhancement"}],
    }

    issues = validate_actor_ontology_payload(payload)
    assert issues == []
