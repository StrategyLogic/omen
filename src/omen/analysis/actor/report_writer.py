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


def attach_strategic_freedom_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    scenario_results = list(artifact.get("scenario_results") or [])
    overview: list[dict[str, Any]] = []
    for result in scenario_results:
        scenario_key = str(result.get("scenario_key") or "")
        freedom = result.get("strategic_freedom") or {}
        overview.append(
            {
                "scenario_key": scenario_key,
                "strategic_freedom_score": float(freedom.get("score", 0.0)),
                "required_count": len(list(freedom.get("required") or [])),
                "warning_count": len(list(freedom.get("warning") or [])),
                "blocking_count": len(list(freedom.get("blocking") or [])),
            }
        )
    artifact["strategic_freedom_overview"] = overview
    return artifact


def write_deterministic_run_artifact(output_path: str | Path, artifact: dict[str, Any]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(artifact, handle, ensure_ascii=False, indent=2)
    return path
