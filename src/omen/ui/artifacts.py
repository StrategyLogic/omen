"""Artifact persistence helpers for Spec 6 UI flow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.ui.case_catalog import normalize_case_id


def _resolve_output_root(output_root: str | Path) -> Path:
    root = Path(output_root)
    if root.is_absolute():
        return root
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / root


def ensure_case_output_dir(case_id: str, output_root: str | Path = "output/case_replay") -> Path:
    root = _resolve_output_root(output_root)
    normalized_id = normalize_case_id(case_id)
    case_dir = root / normalized_id
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def save_json_artifact(case_id: str, filename: str, payload: dict[str, Any]) -> Path:
    case_dir = ensure_case_output_dir(case_id)
    path = case_dir / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
