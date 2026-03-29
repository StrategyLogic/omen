from __future__ import annotations

import pytest
from jsonschema import ValidationError

from ._schema_utils import validate_with_contract


def test_ontology_generation_request_contract_accepts_valid_payload() -> None:
    payload = {
        "case_id": "xd",
        "title": "X-Developer Replay",
        "document": {
            "content_type": "markdown",
            "content": "# Intro\nThe founder launched product milestones.",
            "source_path": "cases/x-developer.md",
            "known_outcome": "gradual adoption",
        },
        "llm_config": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.example.test",
            "api_key": "dummy-key",
            "timeout_seconds": 30,
            "temperature": 0.2,
        },
        "generation_profile": {
            "strict_schema": True,
            "include_case_package": True,
            "seed": 42,
        },
    }

    validate_with_contract(payload, "ontology-generation-request.schema.json")


def test_ontology_generation_request_contract_rejects_missing_llm_config() -> None:
    payload = {
        "case_id": "xd",
        "title": "X-Developer Replay",
        "document": {"content_type": "markdown", "content": "content"},
    }

    with pytest.raises(ValidationError):
        validate_with_contract(payload, "ontology-generation-request.schema.json")
