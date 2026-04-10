"""Deterministic run artifact writer for strategic actor simulation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_fixed_order_scenario_comparison(
    scenario_results: list[dict[str, Any]],
    *,
    order: tuple[str, ...] = ("A", "B", "C"),
) -> dict[str, Any]:
    by_key = {result.get("scenario_key"): result for result in scenario_results}
    ordered = [key for key in order if key in by_key]
    return {
        "order": list(order),
        "executed": ordered,
    }


def attach_evidence_index_and_flags(
    artifact: dict[str, Any],
    *,
    evidence_index: list[dict[str, Any]],
    confidence_flag: str,
) -> dict[str, Any]:
    artifact["evidence_index"] = evidence_index
    artifact["confidence_flags"] = {
        "overall": confidence_flag,
    }
    return artifact


def write_deterministic_run_artifact(output_path: str | Path, artifact: dict[str, Any]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(artifact, handle, ensure_ascii=False, indent=2)
    return path


def write_actor_derivation_artifact(output_path: str | Path, artifact: dict[str, Any]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(artifact, handle, ensure_ascii=False, indent=2)
    return path


def write_reason_chain_artifact(output_path: str | Path, artifact: dict[str, Any]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(artifact, handle, ensure_ascii=False, indent=2)
    return path


def write_reason_chain_view_model_artifact(output_path: str | Path, artifact: dict[str, Any]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(artifact, handle, ensure_ascii=False, indent=2)
    return path
