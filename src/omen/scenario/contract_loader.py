"""Helpers to load spec contract schemas from repository paths."""

from __future__ import annotations

import json
from pathlib import Path


def load_spec4_contract_schema(schema_filename: str) -> dict:
    """Load a schema file from specs/004-improve-inference-precision/contracts/."""

    root = Path(__file__).resolve().parents[3]
    schema_path = (
        root
        / "specs"
        / "004-improve-inference-precision"
        / "contracts"
        / schema_filename
    )
    if not schema_path.exists():
        raise FileNotFoundError(f"Spec 4 contract schema not found: {schema_path}")
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)
