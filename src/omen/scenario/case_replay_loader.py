"""Loader utilities for Spec 6 case replay artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from omen.scenario.ontology_loader import bind_ontology_to_scenario
from omen.scenario.validator import validate_scenario_or_raise
from omen.scenario.ontology_validator import (
    validate_ontology_input_or_raise,
    validate_ontology_input_with_warnings,
)


_DEFAULT_ACTIONS = [
    "grow_semantic_layer",
    "defend_core",
    "attack_competitor",
    "partner_ecosystem",
]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _build_functional_profile(
    actor_id: str,
    capability_rows: list[dict[str, Any]],
) -> dict[str, float]:
    actor_caps = [r for r in capability_rows if str(r.get("actor_id") or "") == actor_id]
    if not actor_caps:
        return {
            "semantic": 0.55,
            "consistency": 0.55,
            "developer_experience": 0.55,
        }

    semantic_scores: list[float] = []
    consistency_scores: list[float] = []
    experience_scores: list[float] = []
    all_scores: list[float] = []

    for row in actor_caps:
        name = str(row.get("name") or "").lower()
        score = float(row.get("score") or 0.0)
        score = _clamp01(score)
        all_scores.append(score)
        if any(token in name for token in ("semantic", "insight", "analysis", "data")):
            semantic_scores.append(score)
        if any(token in name for token in ("process", "automation", "consist", "performance")):
            consistency_scores.append(score)
        if any(token in name for token in ("adoption", "experience", "barrier", "workflow", "developer")):
            experience_scores.append(score)

    avg = sum(all_scores) / len(all_scores) if all_scores else 0.55
    return {
        "semantic": _clamp01(max(semantic_scores) if semantic_scores else avg),
        "consistency": _clamp01(max(consistency_scores) if consistency_scores else avg),
        "developer_experience": _clamp01(max(experience_scores) if experience_scores else avg),
    }


def _normalize_capability_dimensions(capabilities: Any) -> list[dict[str, Any]]:
    if not isinstance(capabilities, list):
        return [{"name": "semantic", "weight": 1.0}]

    rows: list[dict[str, Any]] = []
    if all(isinstance(item, str) for item in capabilities):
        total = max(1, len(capabilities))
        for item in capabilities:
            name = item.strip()
            if name:
                rows.append({"name": name, "weight": 1.0 / total})
        return rows or [{"name": "semantic", "weight": 1.0}]

    valid_rows = [item for item in capabilities if isinstance(item, dict)]
    if not valid_rows:
        return [{"name": "semantic", "weight": 1.0}]

    explicit_weights = [float(item["weight"]) for item in valid_rows if "weight" in item]
    default_weight = 1.0 / max(1, len(valid_rows))
    for item in valid_rows:
        name = str(item.get("name") or item.get("capability_id") or "").strip()
        if not name:
            continue
        weight = float(item.get("weight", default_weight))
        rows.append({"name": name, "weight": weight})

    if not rows:
        return [{"name": "semantic", "weight": 1.0}]

    total_weight = sum(r["weight"] for r in rows)
    if total_weight <= 0:
        for row in rows:
            row["weight"] = 1.0 / len(rows)
        return rows

    for row in rows:
        row["weight"] = row["weight"] / total_weight
    return rows


def _normalize_scenario_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    abox_value = payload.get("abox")
    abox: dict[str, Any] = abox_value if isinstance(abox_value, dict) else {}
    abox_actors_value = abox.get("actors")
    abox_actors: list[Any] = abox_actors_value if isinstance(abox_actors_value, list) else []
    abox_caps_value = abox.get("capabilities")
    abox_caps: list[Any] = abox_caps_value if isinstance(abox_caps_value, list) else []

    actor_type_by_id: dict[str, str] = {}
    for actor in abox_actors:
        if not isinstance(actor, dict):
            continue
        actor_id = str(actor.get("actor_id") or "").strip()
        if not actor_id:
            continue
        actor_type = str(actor.get("actor_type") or actor.get("concept") or "Actor").strip()
        actor_type_by_id[actor_id] = actor_type

    raw_actors_value = payload.get("actors")
    raw_actors: list[Any] = raw_actors_value if isinstance(raw_actors_value, list) else []
    normalized_actors: list[dict[str, Any]] = []
    top_level_actions = payload.get("available_actions")
    if not isinstance(top_level_actions, list) or not top_level_actions:
        top_level_actions = _DEFAULT_ACTIONS

    for index, raw_actor in enumerate(raw_actors):
        if isinstance(raw_actor, str):
            actor_id = raw_actor.strip()
            if not actor_id:
                continue
            normalized_actors.append(
                {
                    "actor_id": actor_id,
                    "actor_type": actor_type_by_id.get(actor_id, "Actor"),
                    "budget": max(300.0, 1000.0 - index * 120.0),
                    "initial_user_base": max(80, 300 - index * 45),
                    "available_actions": list(top_level_actions),
                    "functional_profile": _build_functional_profile(actor_id, abox_caps),
                }
            )
            continue

        if isinstance(raw_actor, dict):
            actor_id = str(raw_actor.get("actor_id") or "").strip()
            if not actor_id:
                continue
            normalized_actors.append(
                {
                    "actor_id": actor_id,
                    "actor_type": str(
                        raw_actor.get("actor_type")
                        or actor_type_by_id.get(actor_id)
                        or "Actor"
                    ).strip(),
                    "budget": float(raw_actor.get("budget", max(300.0, 1000.0 - index * 120.0))),
                    "initial_user_base": int(raw_actor.get("initial_user_base", max(80, 300 - index * 45))),
                    "available_actions": list(raw_actor.get("available_actions") or top_level_actions),
                    "functional_profile": dict(
                        raw_actor.get("functional_profile")
                        or _build_functional_profile(actor_id, abox_caps)
                    ),
                }
            )

    for index, actor in enumerate(abox_actors):
        if not isinstance(actor, dict):
            continue
        actor_id = str(actor.get("actor_id") or "").strip()
        if not actor_id or any(a["actor_id"] == actor_id for a in normalized_actors):
            continue
        normalized_actors.append(
            {
                "actor_id": actor_id,
                "actor_type": str(actor.get("actor_type") or actor.get("concept") or "Actor"),
                "budget": max(300.0, 1000.0 - index * 120.0),
                "initial_user_base": max(80, 300 - index * 45),
                "available_actions": list(top_level_actions),
                "functional_profile": _build_functional_profile(actor_id, abox_caps),
            }
        )

    normalized["actors"] = normalized_actors
    normalized["capabilities"] = _normalize_capability_dimensions(payload.get("capabilities"))
    return normalized


def _build_us1_fallback_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    abox_value = payload.get("abox")
    abox: dict[str, Any] = abox_value if isinstance(abox_value, dict) else {}
    abox_actors_value = abox.get("actors")
    abox_actors: list[Any] = abox_actors_value if isinstance(abox_actors_value, list) else []
    abox_caps_value = abox.get("capabilities")
    abox_caps: list[Any] = abox_caps_value if isinstance(abox_caps_value, list) else []
    top_level_actions = payload.get("available_actions")
    if not isinstance(top_level_actions, list) or not top_level_actions:
        top_level_actions = _DEFAULT_ACTIONS

    fallback_actors: list[dict[str, Any]] = []
    for index, actor in enumerate(abox_actors):
        if not isinstance(actor, dict):
            continue
        actor_id = str(actor.get("actor_id") or "").strip()
        if not actor_id:
            continue
        fallback_actors.append(
            {
                "actor_id": actor_id,
                "actor_type": str(actor.get("actor_type") or actor.get("concept") or "Actor"),
                "budget": max(300.0, 1000.0 - index * 120.0),
                "initial_user_base": max(80, 300 - index * 45),
                "available_actions": list(top_level_actions),
                "functional_profile": _build_functional_profile(actor_id, abox_caps),
            }
        )

    if len(fallback_actors) < 2:
        fallback_actors.append(
            {
                "actor_id": "market_baseline",
                "actor_type": "Actor",
                "budget": 600.0,
                "initial_user_base": 200,
                "available_actions": list(top_level_actions),
                "functional_profile": {
                    "semantic": 0.5,
                    "consistency": 0.5,
                    "developer_experience": 0.5,
                },
            }
        )

    meta_value = payload.get("meta")
    meta: dict[str, Any] = meta_value if isinstance(meta_value, dict) else {}
    scenario_id = str(payload.get("scenario_id") or meta.get("case_id") or "case-replay-us1")
    name = str(payload.get("name") or meta.get("case_title") or "Case Replay Baseline")

    return {
        "scenario_id": scenario_id,
        "name": name,
        "time_steps": int(payload.get("time_steps") or 12),
        "seed": payload.get("seed") if isinstance(payload.get("seed"), int) else 42,
        "user_overlap_threshold": float(payload.get("user_overlap_threshold") or 0.2),
        "actors": fallback_actors,
        "capabilities": _normalize_capability_dimensions(payload.get("capabilities") or []),
    }


def save_strategy_ontology(payload: dict[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def validate_strategy_ontology(payload: dict[str, Any]) -> dict[str, Any]:
    validated, _ = validate_ontology_input_with_warnings(payload)
    return validated.model_dump(mode="python")


def load_case_replay_scenario(
    ontology_path: str | Path,
):
    ontology_payload = json.loads(Path(ontology_path).read_text(encoding="utf-8"))
    ontology, normalization_warnings = validate_ontology_input_with_warnings(ontology_payload)

    ontology_warnings = list(normalization_warnings)
    validated_payload = ontology.model_dump(mode="python")

    normalized_payload = _normalize_scenario_payload(validated_payload)
    try:
        scenario = validate_scenario_or_raise(normalized_payload)
    except ValidationError:
        fallback_payload = _build_us1_fallback_scenario(validated_payload)
        scenario = validate_scenario_or_raise(fallback_payload)
    ontology_setup = bind_ontology_to_scenario(ontology, scenario)
    ontology_setup["ontology_warnings"] = ontology_warnings
    return scenario, ontology_setup
