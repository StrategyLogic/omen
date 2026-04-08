"""Prior snapshot builders for deterministic scenario planning."""

from __future__ import annotations

from typing import Any

from omen.scenario.models import ScenarioPriorProbabilitySnapshotModel


def _normalize_priors(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = sum(float(item.get("score") or 0.0) for item in raw)
    if total <= 0.0:
        total = 1.0
    normalized: list[dict[str, Any]] = []
    for item in raw:
        score = float(item.get("score") or 0.0)
        explain = str(item.get("explain") or "").strip()
        normalized.append(
            {
                "scenario_key": str(item.get("scenario_key") or ""),
                "score": round(score / total, 6),
                "explain": explain,
            }
        )
    return normalized


def build_prior_snapshot(
    *,
    pack_id: str,
    pack_version: str,
    situation_id: str,
    actor_ref: str,
    raw_prior_scores: list[dict[str, Any]],
    planning_query_ref: str,
) -> dict[str, Any]:
    normalized_priors = _normalize_priors(raw_prior_scores)
    snapshot = ScenarioPriorProbabilitySnapshotModel(
        pack_id=pack_id,
        pack_version=pack_version,
        situation_id=situation_id,
        actor_ref=actor_ref,
        raw_prior_scores=raw_prior_scores,
        normalized_priors=normalized_priors,
        planning_query_ref=planning_query_ref,
        snapshot_version="prior_snapshot_v1",
    )
    return snapshot.model_dump()
