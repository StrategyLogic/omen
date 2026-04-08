from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, Draft7Validator
from referencing import Registry, Resource


def contracts_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "contracts"


def load_schema(filename: str) -> tuple[dict[str, Any], Path]:
    path = contracts_dir() / filename
    schema = json.loads(path.read_text(encoding="utf-8"))
    return schema, path


def validate_with_contract(instance: dict[str, Any], filename: str) -> None:
    schema, _schema_path = load_schema(filename)
    resources: list[tuple[str, Resource[Any]]] = []
    for child_path in contracts_dir().glob("*.schema.json"):
        child_schema = json.loads(child_path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(child_schema)
        resources.append((child_path.resolve().as_uri(), resource))
        child_id = str(child_schema.get("$id") or "").strip()
        if child_id:
            resources.append((child_id, resource))

    registry = Registry().with_resources(resources)

    schema_draft = str(schema.get("$schema") or "")
    if "draft-07" in schema_draft:
        Draft7Validator(schema, registry=registry).validate(instance)
        return
    Draft202012Validator(schema, registry=registry).validate(instance)
