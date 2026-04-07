"""LLM scenario decomposition helpers and orchestration."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from omen.ingest.synthesizer.clients import invoke_text_prompt, render_prompt_template
from omen.ingest.synthesizer.prompts import build_json_retry_prompt
from omen.ingest.synthesizer.prompts.registry import get_prompt_template
from omen.ingest.synthesizer.services.errors import LLMJsonValidationAbort


_SCENARIO_SLOT_ORDER = ("A", "B", "C")
_SCENARIO_REQUIRED_FIELDS = (
    "title",
    "goal",
    "target",
    "objective",
    "variables",
    "constraints",
    "tradeoff_pressure",
)


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM response does not contain JSON object")
    payload, _ = decoder.raw_decode(text[start:])
    if not isinstance(payload, dict):
        raise ValueError("LLM response payload is not an object")
    return payload


def _invoke_json(
    prompt: str,
    *,
    config_path: str,
    allow_retry: bool = True,
    stage: str = "llm_json",
) -> dict[str, Any]:
    content = invoke_text_prompt(config_path=config_path, user_prompt=prompt)
    try:
        return _extract_json_object(content)
    except Exception as exc:
        if not allow_retry:
            raise LLMJsonValidationAbort(
                stage=stage,
                reason=str(exc),
                raw_output=content,
            ) from exc
        retry_prompt = build_json_retry_prompt(prompt)
        retry_content = invoke_text_prompt(config_path=config_path, user_prompt=retry_prompt)
        try:
            return _extract_json_object(retry_content)
        except Exception as retry_exc:
            raise LLMJsonValidationAbort(
                stage=stage,
                reason=str(retry_exc),
                raw_output=content,
                retry_output=retry_content,
            ) from retry_exc


def _render_base_prompt(template_key: str, values: dict[str, object]) -> str:
    return render_prompt_template(get_prompt_template(template_key, tier="base"), values)


def _coerce_slot_payloads(raw_scenarios: Any) -> dict[str, Any]:
    by_slot: dict[str, Any] = {}
    non_object_slots: list[str] = []

    if not isinstance(raw_scenarios, list):
        return {
            "by_slot": by_slot,
            "non_object_slots": [*list(_SCENARIO_SLOT_ORDER)],
            "issues": ["`scenarios` is not a JSON array."],
        }

    for index, item in enumerate(raw_scenarios):
        slot = _SCENARIO_SLOT_ORDER[index] if index < len(_SCENARIO_SLOT_ORDER) else None
        if isinstance(item, dict):
            key = str(item.get("scenario_key") or "").strip().upper()
            if key in _SCENARIO_SLOT_ORDER:
                by_slot[key] = item
            elif slot and slot not in by_slot:
                by_slot[slot] = item
            continue

        if slot:
            non_object_slots.append(slot)

    issues: list[str] = []
    if non_object_slots:
        joined = ", ".join(non_object_slots)
        issues.append(f"Non-object scenario payload found at slots: {joined}.")
    for slot in _SCENARIO_SLOT_ORDER:
        if slot not in by_slot:
            issues.append(f"Missing scenario object for slot {slot}.")

    return {
        "by_slot": by_slot,
        "non_object_slots": non_object_slots,
        "issues": issues,
    }


def _is_filled_field(field_name: str, value: Any) -> bool:
    if field_name == "variables":
        return isinstance(value, list) and bool(value)
    if field_name in {"constraints", "tradeoff_pressure"}:
        if not isinstance(value, list):
            return False
        return any(str(item).strip() for item in value)
    return bool(str(value or "").strip())


def _assess_scenario_decomposition_quality(payload: dict[str, Any]) -> dict[str, Any]:
    scenarios = payload.get("scenarios")
    coerced = _coerce_slot_payloads(scenarios)
    by_slot: dict[str, Any] = coerced["by_slot"]
    issues = list(coerced["issues"])

    total_fields = len(_SCENARIO_SLOT_ORDER) * len(_SCENARIO_REQUIRED_FIELDS)
    filled_fields = 0
    slot_completeness: list[dict[str, Any]] = []

    objectives: list[str] = []
    for slot in _SCENARIO_SLOT_ORDER:
        raw = by_slot.get(slot)
        missing_fields: list[str] = []
        if isinstance(raw, dict):
            for field_name in _SCENARIO_REQUIRED_FIELDS:
                if _is_filled_field(field_name, raw.get(field_name)):
                    filled_fields += 1
                else:
                    missing_fields.append(field_name)
            objective = str(raw.get("objective") or "").strip()
            if objective:
                objectives.append(objective)
        else:
            missing_fields = list(_SCENARIO_REQUIRED_FIELDS)

        if missing_fields:
            issues.append(f"Slot {slot} missing fields: {', '.join(missing_fields)}")

        slot_completeness.append(
            {
                "scenario_key": slot,
                "filled": len(_SCENARIO_REQUIRED_FIELDS) - len(missing_fields),
                "total": len(_SCENARIO_REQUIRED_FIELDS),
                "missing_fields": missing_fields,
            }
        )

    completeness_ratio = filled_fields / total_fields if total_fields else 0.0
    objectives_unique = len({text.lower() for text in objectives})
    logic_issues: list[str] = []
    if objectives_unique < 2:
        logic_issues.append("Scenario objectives are not sufficiently differentiated across A/B/C.")
    if completeness_ratio < 0.5:
        logic_issues.append("Schema completeness below minimum usable threshold (50%).")

    logic_usable = not logic_issues

    return {
        "schema_completeness_percent": round(completeness_ratio * 100.0, 2),
        "schema_completeness_ratio": round(completeness_ratio, 4),
        "slot_completeness": slot_completeness,
        "logic_usable": logic_usable,
        "logic_issues": logic_issues,
        "validation_issues": issues,
    }


def _normalize_decomposition_payload(payload: dict[str, Any]) -> dict[str, Any]:
    scenarios = payload.get("scenarios")
    normalized_scenarios: list[Any]

    if isinstance(scenarios, dict):
        normalized_scenarios = []
        for slot in _SCENARIO_SLOT_ORDER:
            raw = scenarios.get(slot)
            if isinstance(raw, dict):
                item = dict(raw)
                item.setdefault("scenario_key", slot)
                normalized_scenarios.append(item)
        payload["scenarios"] = normalized_scenarios
    elif isinstance(scenarios, list):
        normalized_scenarios = []
        for index, raw in enumerate(scenarios):
            if not isinstance(raw, dict):
                normalized_scenarios.append(raw)
                continue

            item = dict(raw)
            key = str(item.get("scenario_key") or "").strip().upper()
            if key not in _SCENARIO_SLOT_ORDER and index < len(_SCENARIO_SLOT_ORDER):
                key = _SCENARIO_SLOT_ORDER[index]
            if key in _SCENARIO_SLOT_ORDER:
                item["scenario_key"] = key
            normalized_scenarios.append(item)
        payload["scenarios"] = normalized_scenarios
    else:
        return payload

    for raw in payload.get("scenarios") or []:
        if not isinstance(raw, dict):
            continue

        if not str(raw.get("title") or "").strip():
            slot = str(raw.get("scenario_key") or "").strip().upper()
            goal_text = str(raw.get("goal") or "").strip()
            if goal_text:
                raw["title"] = f"Scenario {slot or '?'}: {goal_text}"

        tradeoff = raw.get("tradeoff_pressure")
        if isinstance(tradeoff, str):
            text = tradeoff.strip()
            raw["tradeoff_pressure"] = [text] if text else []

        notes = raw.get("modeling_notes")
        if isinstance(notes, str):
            text = notes.strip()
            raw["modeling_notes"] = [text] if text else []

    return payload


def decompose_scenario_from_situation(
    *,
    situation_artifact: dict[str, Any],
    pack_id: str,
    pack_version: str,
    config_path: str = "config/llm.toml",
    planning_template: dict[str, Any] | None = None,
    planning_query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_prompt = _render_base_prompt(
        "situation_decompose_prompt",
        {
            "pack_id": pack_id,
            "pack_version": pack_version,
            "situation_artifact_json": json.dumps(situation_artifact, ensure_ascii=False),
            "planning_template_json": json.dumps(planning_template or {}, ensure_ascii=False),
            "planning_query_json": json.dumps(planning_query or {}, ensure_ascii=False),
        },
    )
    payload = _invoke_json(
        base_prompt,
        config_path=config_path,
        stage="situation_decompose_prompt",
    )
    payload = _normalize_decomposition_payload(payload)
    quality = _assess_scenario_decomposition_quality(payload)

    retries = 0
    if quality["schema_completeness_ratio"] < 0.5:
        retry_prompt = (
            f"{base_prompt}\n\n"
            "Previous decomposition payload had low schema completeness. "
            "Return a corrected JSON object with three structured scenario objects for A/B/C.\n"
            f"Previous payload: {json.dumps(payload, ensure_ascii=False)}"
        )
        payload = _invoke_json(
            retry_prompt,
            config_path=config_path,
            stage="situation_decompose_prompt",
        )
        payload = _normalize_decomposition_payload(payload)
        quality = _assess_scenario_decomposition_quality(payload)
        retries = 1

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
    payload["decomposition_quality"] = {
        **quality,
        "retries": retries,
    }
    return payload
