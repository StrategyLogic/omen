"""Founder ontology loader with basic consistency checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.ingest.llm_ontology.actor_builder import founder_hash


class FounderSliceLoadError(ValueError):
    """Raised when founder ontology loading or integrity check fails."""


def load_founder_ontology(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FounderSliceLoadError(f"founder ontology not found: {file_path}")
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise FounderSliceLoadError("founder ontology must be a JSON object")
    return payload


def validate_founder_ref(
    strategy_ontology: dict[str, Any],
    founder_ontology: dict[str, Any],
) -> None:
    # Validation must be read-only for analysis-time checks.
    ref_raw = strategy_ontology.get("founder_ref")
    if not isinstance(ref_raw, dict):
        raise FounderSliceLoadError("strategy ontology missing founder_ref")
    ref = dict(ref_raw)

    strategy_case_id = str(((strategy_ontology.get("meta") or {}).get("case_id") or "")).strip()
    founder_case_id = str(((founder_ontology.get("meta") or {}).get("case_id") or "")).strip()
    if strategy_case_id != founder_case_id:
        raise FounderSliceLoadError(
            f"case_id mismatch between strategy ({strategy_case_id}) and founder ({founder_case_id})"
        )

    expected_hash = str(ref.get("hash") or "").strip()
    actual_hash = founder_hash(founder_ontology)
    if expected_hash and expected_hash != actual_hash:
        raise FounderSliceLoadError(
            f"founder hash mismatch: expected {expected_hash}, got {actual_hash}"
        )
