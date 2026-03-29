from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, Draft7Validator, RefResolver


def contracts_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "specs" / "006-startup-case-replay" / "contracts"


def load_schema(filename: str) -> tuple[dict[str, Any], Path]:
    path = contracts_dir() / filename
    schema = json.loads(path.read_text(encoding="utf-8"))
    return schema, path


def validate_with_contract(instance: dict[str, Any], filename: str) -> None:
    schema, schema_path = load_schema(filename)
    base_uri = schema_path.resolve().as_uri()
    store: dict[str, Any] = {}
    for child_path in contracts_dir().glob("*.schema.json"):
        child_schema = json.loads(child_path.read_text(encoding="utf-8"))
        store[child_path.resolve().as_uri()] = child_schema
        child_id = str(child_schema.get("$id") or "").strip()
        if child_id:
            store[child_id] = child_schema

    resolver = RefResolver(base_uri=base_uri, referrer=schema, store=store)

    schema_draft = str(schema.get("$schema") or "")
    if "draft-07" in schema_draft:
        Draft7Validator(schema, resolver=resolver).validate(instance)
        return
    Draft202012Validator(schema, resolver=resolver).validate(instance)
