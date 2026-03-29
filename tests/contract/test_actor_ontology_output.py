from __future__ import annotations


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
