from __future__ import annotations

import json
from pathlib import Path


def _contracts_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "specs" / "006-startup-case-replay" / "contracts"


def test_contract_schemas_are_valid_json() -> None:
    schema_files = sorted(_contracts_dir().glob("*.schema.json"))
    assert schema_files
    for schema_file in schema_files:
        payload = json.loads(schema_file.read_text(encoding="utf-8"))
        assert isinstance(payload, dict), f"schema {schema_file.name} must be a JSON object"
