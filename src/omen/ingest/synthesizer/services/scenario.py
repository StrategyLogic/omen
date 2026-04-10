"""LLM scenario decomposition helpers and orchestration."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from omen.ingest.writer.markdown import render_scenario_ontology_markdown
from omen.ingest.synthesizer.builders.scenario import (
    build_scenario_ontology_from_decomposition,
    bind_ontology_to_scenario,
    load_ontology_input,
    normalize_scenario_ontology_scenarios,
)
from omen.ingest.synthesizer.clients import invoke_text_prompt, render_prompt_template
from omen.ingest.synthesizer.prompts import build_json_retry_prompt
from omen.ingest.synthesizer.prompts.registry import get_prompt_template
from omen.ingest.synthesizer.services.errors import LLMJsonValidationAbort
from omen.ingest.validators.scenario import (
    ScenarioConfig,
    validate_case_package_or_raise,
    validate_deterministic_scenario_pack_or_raise,
    validate_scenario_ontology_slice_or_raise,
    validate_scenario_or_raise,
)
from omen.ingest.validators.strategy import validate_ontology_input_or_raise
from omen.types import CasePackage


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


def _assess_quality(payload: dict[str, Any]) -> dict[str, Any]:
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


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
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


def planning(
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
    payload = _normalize(payload)
    quality = _assess_quality(payload)

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
        payload = _normalize(payload)
        quality = _assess_quality(payload)
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


def normalize_scenarios(llm_scenarios: list[Any]) -> list[dict[str, Any]]:
    return normalize_scenario_ontology_scenarios(llm_scenarios)


def build_ontology(
    *,
    situation_artifact: dict[str, Any],
    llm_decomposition: dict[str, Any],
    pack_id: str,
    pack_version: str,
) -> dict[str, Any]:
    return build_scenario_ontology_from_decomposition(
        situation_artifact=situation_artifact,
        llm_decomposition=llm_decomposition,
        pack_id=pack_id,
        pack_version=pack_version,
    )


def load(path: str | Path) -> dict[str, Any]:
    scenario_path = Path(path)
    payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    validated = validate_scenario_ontology_slice_or_raise(payload)
    return validated.model_dump()


def pack(ontology: dict[str, Any]) -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []
    for scenario in ontology.get("scenarios", []):
        if not isinstance(scenario, dict):
            continue
        resistance = dict(scenario.get("resistance_assumptions") or {})
        scenarios.append(
            {
                "scenario_key": scenario["scenario_key"],
                "title": scenario["title"],
                "target_outcome": scenario["objective"],
                "constraints": list(scenario.get("constraints") or []),
                "dilemma_tradeoffs": list(scenario.get("tradeoff_pressure") or []),
                "resistance_baseline": {
                    "structural_conflict": resistance["structural_conflict"],
                    "resource_reallocation_drag": resistance["resource_reallocation_drag"],
                    "cultural_misalignment": resistance["cultural_misalignment"],
                    "veto_node_intensity": resistance["veto_node_intensity"],
                    "aggregate_resistance": resistance["aggregate_resistance"],
                },
            }
        )

    return {
        "pack_id": ontology["pack_id"],
        "pack_version": ontology["pack_version"],
        "scenarios": scenarios,
    }


def prepare(path: str | Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    ontology = load(path)
    deterministic_pack = pack(ontology)
    validated_pack = validate_deterministic_scenario_pack_or_raise(deterministic_pack)
    planned_scenarios = {
        str(item.get("scenario_key") or ""): dict(item)
        for item in list(ontology.get("scenarios") or [])
        if isinstance(item, dict)
    }
    return validated_pack.model_dump(), planned_scenarios


def load_scenario(path: str | Path) -> ScenarioConfig:
    scenario_path = Path(path)
    with scenario_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return validate_scenario_or_raise(payload)


def load_case_package(path: str | Path) -> CasePackage:
    package_path = Path(path)
    with package_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return validate_case_package_or_raise(payload, base_dir=package_path.parent.parent)


def load_case_package_from_scenario(path: str | Path) -> CasePackage:
    scenario_path = Path(path)
    with scenario_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    case_package_payload = payload.get("case_package")
    if not isinstance(case_package_payload, dict):
        raise ValueError("scenario missing `case_package` object")

    return validate_case_package_or_raise(case_package_payload, base_dir=scenario_path.parent.parent.parent)


def load_scenario_with_ontology(
    scenario_path: str | Path,
    ontology_path: str | Path | None = None,
) -> tuple[ScenarioConfig, dict[str, Any] | None]:
    scenario_path = Path(scenario_path)
    with scenario_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    scenario = validate_scenario_or_raise(payload)

    ontology = None
    if ontology_path is not None:
        ontology = load_ontology_input(ontology_path)
    elif isinstance(payload, dict) and all(key in payload for key in ("meta", "tbox", "abox")):
        ontology = validate_ontology_input_or_raise(payload)

    if ontology is None:
        return scenario, None

    ontology_metadata = bind_ontology_to_scenario(ontology, scenario)
    return scenario, ontology_metadata


def load_scenario_ontology_slice(path: str | Path) -> dict[str, Any]:
    scenario_path = Path(path)
    with scenario_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    validated = validate_scenario_ontology_slice_or_raise(payload)
    return validated.model_dump()


def save_scenario_ontology_slice(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    validated = validate_scenario_ontology_slice_or_raise(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(validated.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def save_scenario_ontology_markdown(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    validated = validate_scenario_ontology_slice_or_raise(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_scenario_ontology_markdown(validated.model_dump())
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def resolve_scenario_artifact_ref(ref: str | Path) -> Path:
    raw = str(ref).strip()
    if not raw:
        raise ValueError("empty scenario reference")

    candidate = Path(raw)
    if candidate.exists():
        return candidate

    return Path("data/scenarios") / raw / "scenario_pack.json"
