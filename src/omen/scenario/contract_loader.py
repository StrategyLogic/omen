"""Helpers to load spec contract schemas from repository paths."""

from __future__ import annotations

import json
from pathlib import Path


def load(schema_filename: str) -> dict:
    """Load a schema from the repo spec path, with a test-fixture fallback."""

    root = Path(__file__).resolve().parents[3]
    schema_path = (
        root
        / "tests"
            / "fixtures"
            / "contracts"
        / schema_filename
    )
    if not schema_path.exists():
        raise FileNotFoundError(f"Spec 4 contract schema not found: {schema_path}")
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)
