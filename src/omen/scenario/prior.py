"""Prior snapshot builders for deterministic scenario planning."""

from __future__ import annotations

import json
from typing import Any

from omen.ingest.synthesizer.clients import invoke_text_prompt, render_prompt_template
from omen.ingest.synthesizer.prompts import build_json_retry_prompt
from omen.ingest.synthesizer.prompts.registry import get_prompt_template
from omen.analysis.actor.formation import extract_strategic_actor_style_payload
from omen.analysis.actor.formation import load_actor_ontology_payload
from omen.scenario.models import ScenarioPriorProbabilitySnapshotModel


def _render_base_prompt(template_key: str, values: dict[str, object]) -> str:
    return render_prompt_template(get_prompt_template(template_key, tier="base"), values)


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM response does not contain JSON object")
    payload, _ = decoder.raw_decode(text[start:])
    if not isinstance(payload, dict):
        raise ValueError("LLM response payload is not an object")
    return payload


def _invoke_json(prompt: str, *, config_path: str, stage: str) -> dict[str, Any]:
    _ = stage
    content = invoke_text_prompt(config_path=config_path, user_prompt=prompt)
    try:
        return _extract_json_object(content)
    except Exception:
        retry_prompt = build_json_retry_prompt(prompt)
        retry_content = invoke_text_prompt(config_path=config_path, user_prompt=retry_prompt)
        return _extract_json_object(retry_content)


def _build_prior_candidates_from_scenarios(ontology: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in list(ontology.get("scenarios") or []):
        if not isinstance(item, dict):
            continue
        scenario_key = str(item.get("scenario_key") or "").strip().upper()
        if scenario_key not in {"A", "B", "C"}:
            continue
        candidates.append(
            {
                "scenario_key": scenario_key,
                "title": str(item.get("title") or "").strip(),
                "goal": str(item.get("goal") or "").strip(),
                "target": str(item.get("target") or "").strip(),
                "objective": str(item.get("objective") or "").strip(),
                "constraints": [str(x).strip() for x in list(item.get("constraints") or []) if str(x).strip()],
                "tradeoff_pressure": [
                    str(x).strip() for x in list(item.get("tradeoff_pressure") or []) if str(x).strip()
                ],
            }
        )
    if len(candidates) != 3:
        raise ValueError("scenario ontology must provide A/B/C candidates for prior scoring")
    return sorted(candidates, key=lambda x: x["scenario_key"])


def score_prior_probabilities(
    *,
    actor_ref: str,
    scenario_ontology: dict[str, Any],
    planning_query: dict[str, Any],
    config_path: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    actor_payload = load_actor_ontology_payload(actor_ref)
    actor_style = extract_strategic_actor_style_payload(actor_payload)
    scenario_candidates = _build_prior_candidates_from_scenarios(scenario_ontology)
    prompt = _render_base_prompt(
        "scenario_prior_prompt",
        {
            "actor_ref": actor_ref,
            "actor_style_json": json.dumps(actor_style, ensure_ascii=False),
            "scenario_candidates_json": json.dumps(scenario_candidates, ensure_ascii=False),
            "fallback_similarity_json": json.dumps(planning_query.get("similarity_scores") or [], ensure_ascii=False),
        },
    )
    payload = _invoke_json(prompt, config_path=config_path, stage="scenario_prior_prompt")
    items = payload.get("raw_prior_scores")
    if not isinstance(items, list):
        raise ValueError("scenario_prior_prompt output must include raw_prior_scores array")

    scored: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("scenario_key") or "").strip().upper()
        if key not in {"A", "B", "C"}:
            continue
        score = float(item.get("score") or 0.0)
        explain = str(item.get("explain") or "").strip()
        if score < 0.0:
            raise ValueError(f"scenario_prior_prompt produced negative score for {key}")
        if not explain:
            raise ValueError(f"scenario_prior_prompt produced empty explain for {key}")
        scored.append({"scenario_key": key, "score": score, "explain": explain})

    if sorted(item["scenario_key"] for item in scored) != ["A", "B", "C"]:
        raise ValueError("scenario_prior_prompt must provide A/B/C exactly once")

    trace = {
        "stage": "scenario_prior_prompt",
        "status": "ok",
        "reason": "scenario_prior_prompt scored A/B/C with explanations",
        "scoring_source": "llm",
    }
    return sorted(scored, key=lambda item: item["scenario_key"]), trace


def _normalize_priors(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not raw:
        return []

    cleaned: list[dict[str, Any]] = []
    for item in raw:
        cleaned.append(
            {
                "scenario_key": str(item.get("scenario_key") or ""),
                "score": max(0.0, float(item.get("score") or 0.0)),
                "explain": str(item.get("explain") or "").strip(),
            }
        )

    total = sum(float(item["score"]) for item in cleaned)
    if total <= 0.0:
        uniform = 1.0 / float(len(cleaned))
        return [
            {
                "scenario_key": item["scenario_key"],
                "score": uniform,
                "explain": item["explain"],
            }
            for item in cleaned
        ]

    normalized: list[dict[str, Any]] = []
    running_total = 0.0
    last_index = len(cleaned) - 1
    for index, item in enumerate(cleaned):
        if index == last_index:
            score = max(0.0, 1.0 - running_total)
        else:
            score = float(item["score"]) / total
            running_total += score
        normalized.append(
            {
                "scenario_key": item["scenario_key"],
                "score": score,
                "explain": item["explain"],
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
