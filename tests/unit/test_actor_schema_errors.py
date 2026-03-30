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
