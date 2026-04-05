"""LLM pipeline for situation analyze and scenario decomposition."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from omen.ingest.llm_ontology.clients import create_chat_client
from omen.ingest.llm_ontology.config import load_llm_config
from omen.ingest.llm_ontology.prompts import build_json_retry_prompt


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM response does not contain JSON object")
    payload, _ = decoder.raw_decode(text[start:])
    if not isinstance(payload, dict):
        raise ValueError("LLM response payload is not an object")
    return payload


def _invoke_json(prompt: str, *, config_path: str) -> dict[str, Any]:
    config = load_llm_config(config_path)
    chat = create_chat_client(config)
    response = chat.invoke(prompt)
    content = response.content if isinstance(response.content, str) else json.dumps(response.content)
    try:
        return _extract_json_object(content)
    except Exception:
        retry_prompt = build_json_retry_prompt(prompt)
        retry_response = chat.invoke(retry_prompt)
        retry_content = (
            retry_response.content
            if isinstance(retry_response.content, str)
            else json.dumps(retry_response.content)
        )
        return _extract_json_object(retry_content)


def _read_source_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _as_dict_list(value: Any, *, key_name: str = "name") -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            normalized.append(item)
            continue
        text = str(item).strip()
        if text:
            normalized.append({key_name: text})
    return normalized


def _normalize_uncertainty_space(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        output = dict(value)
        output.setdefault("overall_confidence", 0.5)
        output.setdefault("high_leverage_unknowns", [])
        output.setdefault("assumptions_explicit", [])
        return output

    if isinstance(value, list):
        unknowns = [str(item).strip() for item in value if str(item).strip()]
        return {
            "overall_confidence": 0.5,
            "high_leverage_unknowns": unknowns,
            "assumptions_explicit": [],
        }

    return {
        "overall_confidence": 0.5,
        "high_leverage_unknowns": [],
        "assumptions_explicit": [],
    }


def _normalize_source_trace(value: Any, *, source_path: str, situation_id: str) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]

    if isinstance(value, dict):
        return [value]

    return [
        {
            "situation_id": situation_id,
            "source_path": source_path,
        }
    ]


def _build_extract_prompt(*, source_text: str, source_path: str, actor_ref: str | None) -> str:
    return (
        "You are a strategy analyst. Extract SituationContext from the source document.\n"
        "Return ONLY valid JSON object with keys: "
        "title, core_question, current_state, core_dilemma, key_decision_point, "
        "target_outcomes (array), hard_constraints (array), known_unknowns (array).\n"
        f"actor_ref: {actor_ref or 'none'}\n"
        f"source_path: {source_path}\n"
        "source_document:\n"
        f"{source_text}\n"
    )


def _build_enhance_prompt(*, source_text: str, source_path: str, context: dict[str, Any], situation_id: str) -> str:
    return (
        "You are a strategy analyst. Build Situation_v0_1_0 from source document and context.\n"
        "Return ONLY valid JSON object with keys: "
        "version, id, context, signals, tech_space_seed, market_space_seed, uncertainty_space, source_trace.\n"
        "Rules:\n"
        "- version must be '0.1.0'\n"
        "- id must equal provided situation_id\n"
        "- context must preserve all provided context fields\n"
        "- signals must be non-empty\n"
        f"situation_id: {situation_id}\n"
        f"source_path: {source_path}\n"
        f"context_json: {json.dumps(context, ensure_ascii=False)}\n"
        "source_document:\n"
        f"{source_text}\n"
    )


def _build_scenario_prompt(*, situation_artifact: dict[str, Any], pack_id: str, pack_version: str) -> str:
    return (
        "You are a strategy analyst. Decompose situation artifact into deterministic scenarios A/B/C.\n"
        "Return ONLY valid JSON object with keys: pack_id, pack_version, derived_from_situation_id, ontology_version, scenarios.\n"
        "Scenario requirements:\n"
        "- Must include exactly A, B, C each once\n"
        "- A intent: Aggressive/Alternative challenger, optimistic positive-signal assumptions\n"
        "- B intent: Baseline/Conservative maintainer, linear extrapolation from current state\n"
        "- C intent: Collapse/Contingency extreme-risk, negative-signal breakout\n"
        "- each scenario must include goal, target, objective, variables, constraints, tradeoff_pressure, resistance_assumptions, modeling_notes\n"
        f"pack_id: {pack_id}\n"
        f"pack_version: {pack_version}\n"
        f"situation_artifact_json: {json.dumps(situation_artifact, ensure_ascii=False)}\n"
    )


def analyze_situation_document(
    *,
    situation_file: str | Path,
    actor_ref: str | None,
    pack_id: str,
    pack_version: str,
    config_path: str = "config/llm.toml",
) -> dict[str, Any]:
    path = Path(situation_file)
    source_text = _read_source_text(path)
    situation_id = path.stem

    context = _invoke_json(
        _build_extract_prompt(
            source_text=source_text,
            source_path=str(path),
            actor_ref=actor_ref,
        ),
        config_path=config_path,
    )

    enhanced = _invoke_json(
        _build_enhance_prompt(
            source_text=source_text,
            source_path=str(path),
            context=context,
            situation_id=situation_id,
        ),
        config_path=config_path,
    )

    enhanced.setdefault("version", "0.1.0")
    enhanced.setdefault("id", situation_id)
    enhanced.setdefault("context", context)
    enhanced["signals"] = _as_dict_list(enhanced.get("signals"), key_name="name")
    if not enhanced["signals"]:
        enhanced["signals"] = [{"name": "Signal extracted from source document"}]
    enhanced["tech_space_seed"] = _as_dict_list(enhanced.get("tech_space_seed"), key_name="name")
    enhanced["market_space_seed"] = _as_dict_list(enhanced.get("market_space_seed"), key_name="name")
    enhanced["uncertainty_space"] = _normalize_uncertainty_space(enhanced.get("uncertainty_space"))
    enhanced["source_trace"] = _normalize_source_trace(
        enhanced.get("source_trace"),
        source_path=str(path),
        situation_id=situation_id,
    )
    enhanced["source_meta"] = {
        "source_path": str(path),
        "generated_at": datetime.now().isoformat(),
        "pack_id": pack_id,
        "pack_version": pack_version,
        "actor_ref": actor_ref,
    }
    return enhanced


def decompose_scenario_from_situation(
    *,
    situation_artifact: dict[str, Any],
    pack_id: str,
    pack_version: str,
    config_path: str = "config/llm.toml",
) -> dict[str, Any]:
    payload = _invoke_json(
        _build_scenario_prompt(
            situation_artifact=situation_artifact,
            pack_id=pack_id,
            pack_version=pack_version,
        ),
        config_path=config_path,
    )

    payload.setdefault("pack_id", pack_id)
    payload.setdefault("pack_version", pack_version)
    payload.setdefault("derived_from_situation_id", str(situation_artifact.get("id") or "unknown"))
    payload.setdefault("ontology_version", "scenario_ontology_v1")
    payload.setdefault("scenarios", [])
    payload.setdefault(
        "source_meta",
        {
            "source_path": str((situation_artifact.get("source_meta") or {}).get("source_path") or ""),
            "generated_at": datetime.now().isoformat(),
            "generated_from": "situation_artifact",
        },
    )
    return payload
