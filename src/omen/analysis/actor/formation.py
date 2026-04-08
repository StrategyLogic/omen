"""Scenario result assembly helpers for deterministic strategic actor simulation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.ingest.synthesizer.clients import invoke_text_prompt, render_prompt_template
from omen.ingest.synthesizer.prompts import build_json_retry_prompt
from omen.ingest.synthesizer.prompts.registry import get_prompt_template


def assemble_capability_dilemma_fit(
    *,
    scenario_key: str,
    capability_scores: dict[str, float],
) -> dict[str, Any]:
    if not capability_scores:
        fit = "medium"
    else:
        avg = sum(capability_scores.values()) / max(len(capability_scores), 1)
        fit = "high" if avg >= 0.7 else "low" if avg <= 0.4 else "medium"

    return {
        "scenario_key": scenario_key,
        "fit": fit,
        "capability_scores": capability_scores,
    }


def project_scenario_selected_dimensions(
    *,
    scenario_key: str,
    capability_scores: dict[str, float],
    scenario_ontology: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ranked = sorted(capability_scores.items(), key=lambda item: item[1], reverse=True)
    selected = [key for key, _ in ranked[:2]] if ranked else []

    scene = scenario_ontology or {}
    objective = str(scene.get("objective") or "").strip()
    constraints = [str(item).strip() for item in (scene.get("constraints") or []) if str(item).strip()]
    tradeoff_pressure = [str(item).strip() for item in (scene.get("tradeoff_pressure") or []) if str(item).strip()]

    if scenario_key == "A":
        rationale = [
            "Prioritize offense dimensions from planned scene objective and constraints",
            f"Objective alignment: {objective or 'offense objective from scene'}",
        ]
    elif scenario_key == "B":
        rationale = [
            "Prioritize defense dimensions under planned hard-constraint pressure",
            f"Constraint focus: {', '.join(constraints[:2]) if constraints else 'defense constraints'}",
        ]
    else:
        rationale = [
            "Prioritize confrontation dimensions under direct rivalry tradeoff pressure",
            f"Tradeoff focus: {', '.join(tradeoff_pressure[:2]) if tradeoff_pressure else 'confrontation tradeoff'}",
        ]

    if selected:
        rationale.append(f"Selected highest-capability dimensions: {', '.join(selected)}")

    return {
        "scenario_key": scenario_key,
        "selected_dimension_keys": selected,
        "selection_rationale": rationale,
    }


def _render_base_prompt(template_key: str, values: dict[str, object]) -> str:
    return render_prompt_template(get_prompt_template(template_key, tier="base"), values)


def _extract_json_object(text: str) -> dict[str, object]:
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM response does not contain JSON object")
    payload, _ = decoder.raw_decode(text[start:])
    if not isinstance(payload, dict):
        raise ValueError("LLM response payload is not an object")
    return payload


def _invoke_json(prompt: str, *, config_path: str, stage: str) -> dict[str, object]:
    _ = stage
    content = invoke_text_prompt(config_path=config_path, user_prompt=prompt)
    try:
        return _extract_json_object(content)
    except Exception:
        retry_prompt = build_json_retry_prompt(prompt)
        retry_content = invoke_text_prompt(config_path=config_path, user_prompt=retry_prompt)
        return _extract_json_object(retry_content)


def load_actor_ontology_payload(actor_ref: str) -> dict[str, Any]:
    path = Path(str(actor_ref).strip())
    if not path.exists() or path.suffix.lower() != ".json":
        raise ValueError(f"actor_ref must point to existing actor ontology json: {actor_ref}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("actor ontology payload must be a JSON object")
    return payload


def write_actor_ontology_payload(actor_ref: str, payload: dict[str, Any]) -> None:
    path = Path(str(actor_ref).strip())
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def find_strategic_actor(payload: dict[str, Any]) -> dict[str, Any]:
    actors = payload.get("actors") or []
    if not isinstance(actors, list):
        raise ValueError("actor ontology payload missing actors list")
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        if str(actor.get("type") or "").strip() == "StrategicActor":
            return actor
    raise ValueError("actor ontology payload missing StrategicActor")


def is_strategic_style_admissible(payload: dict[str, Any]) -> bool:
    strategic_actor = find_strategic_actor(payload)
    profile = strategic_actor.get("profile") or {}
    style = profile.get("strategic_style") or {}
    if not isinstance(style, dict):
        return False

    filled = 0
    if str(style.get("decision_style") or "").strip():
        filled += 1
    if str(style.get("value_proposition") or "").strip():
        filled += 1
    if isinstance(style.get("decision_preferences"), list) and any(str(x).strip() for x in style["decision_preferences"]):
        filled += 1
    if isinstance(style.get("non_negotiables"), list) and any(str(x).strip() for x in style["non_negotiables"]):
        filled += 1
    return filled >= 2


def extract_strategic_actor_identity(payload: dict[str, Any]) -> tuple[str, str]:
    strategic_actor = find_strategic_actor(payload)
    return (
        str(strategic_actor.get("name") or "unknown_strategic_actor").strip(),
        str(strategic_actor.get("role") or "").strip(),
    )


def extract_strategic_actor_style_payload(payload: dict[str, Any]) -> dict[str, Any]:
    strategic_actor = find_strategic_actor(payload)
    profile = strategic_actor.get("profile") or {}
    style = profile.get("strategic_style") or {}
    if not isinstance(style, dict):
        raise ValueError("StrategicActor profile.strategic_style must be an object")
    return {
        "name": str(strategic_actor.get("name") or "").strip(),
        "role": str(strategic_actor.get("role") or "").strip(),
        "strategic_style": style,
    }


def apply_enhanced_strategic_style(payload: dict[str, Any], enhanced: dict[str, Any]) -> bool:
    strategic_actor = find_strategic_actor(payload)
    profile = strategic_actor.setdefault("profile", {})
    if not isinstance(profile, dict):
        raise ValueError("StrategicActor profile must be an object")

    existing = profile.get("strategic_style")
    if not isinstance(existing, dict):
        existing = {}
        profile["strategic_style"] = existing

    candidate = enhanced.get("strategic_style") if isinstance(enhanced.get("strategic_style"), dict) else enhanced
    if not isinstance(candidate, dict):
        raise ValueError("scenario_enhance_prompt response must provide strategic_style object")

    changed = False
    for field in ("decision_style", "value_proposition"):
        value = str(candidate.get(field) or "").strip()
        if value and str(existing.get(field) or "").strip() != value:
            existing[field] = value
            changed = True

    for field in ("decision_preferences", "non_negotiables"):
        raw = candidate.get(field)
        if isinstance(raw, list):
            normalized = [str(item).strip() for item in raw if str(item).strip()]
            if normalized and normalized != existing.get(field):
                existing[field] = normalized
                changed = True

    return changed


def ensure_strategic_actor_style(
    *,
    actor_ref: str,
    current_case_id_to_exclude: str,
    config_path: str,
) -> dict[str, object]:
    payload = load_actor_ontology_payload(actor_ref)
    trace: dict[str, object] = {
        "stage": "scenario_enhance_prompt",
        "actor_ref": actor_ref,
        "admissible_before": is_strategic_style_admissible(payload),
        "enhanced": False,
        "status": "noop",
        "reason": "",
    }

    if bool(trace["admissible_before"]):
        trace["reason"] = "strategic actor already admissible"
        return trace

    strategic_actor_name, strategic_actor_role = extract_strategic_actor_identity(payload)
    prompt = _render_base_prompt(
        "scenario_enhance_prompt",
        {
            "actor_ref": actor_ref,
            "strategic_actor_name": strategic_actor_name,
            "strategic_actor_role": strategic_actor_role,
            "current_case_id_to_exclude": current_case_id_to_exclude,
            "actor_ontology_json": json.dumps(payload, ensure_ascii=False),
        },
    )
    enhanced = _invoke_json(prompt, config_path=config_path, stage="scenario_enhance_prompt")
    changed = apply_enhanced_strategic_style(payload, enhanced)
    if not changed:
        raise ValueError("scenario_enhance_prompt returned no applicable strategic_style changes")

    write_actor_ontology_payload(actor_ref, payload)
    trace["enhanced"] = True
    trace["status"] = "updated"
    trace["reason"] = "strategic_style enhanced and persisted"
    return trace
