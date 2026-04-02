"""Compile natural language scenario descriptions into deterministic scenario packs."""

from __future__ import annotations

from typing import Any

from omen.scenario.ingest_validator import (
    AmbiguousScenarioDescriptionError,
    DeferredScopeFeatureError,
    IncompleteDeterministicPackError,
)
from omen.scenario.ontology_models import ScenarioCompilationRequest

_REQUIRED_SLOTS = ("A", "B", "C")

_SLOT_ALIASES: dict[str, str] = {
    "a": "A",
    "slot_a": "A",
    "internal": "A",
    "internal_ecosystem": "A",
    "meego": "A",
    "symbian": "A",
    "内部": "A",
    "内部生态": "A",
    "正面": "A",
    "正面硬刚": "A",
    "b": "B",
    "slot_b": "B",
    "open": "B",
    "open_alliance": "B",
    "android": "B",
    "联盟": "B",
    "开放": "B",
    "牵手android": "B",
    "c": "C",
    "slot_c": "C",
    "platform": "C",
    "platform_alliance": "C",
    "microsoft": "C",
    "微软": "C",
    "微软联盟": "C",
    "外部平台": "C",
}

_DEFERRED_DYNAMIC_KEYS = {
    "dynamic_authoring",
    "dynamic_scenarios",
    "free_form_scenarios",
    "scenario_generator",
}

_DEFERRED_SCENARIO_KEYS = {
    "dynamic_variants",
    "alternative_branches",
    "free_form_prompt",
    "free_form_constraints",
}


def _normalize_lines(text: str) -> list[str]:
    normalized = (
        text.replace("；", "\n")
        .replace(";", "\n")
        .replace("。", "\n")
    )
    lines = [line.strip() for line in normalized.splitlines()]
    return [line for line in lines if line]


def _normalize_label(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _infer_slot_from_text(title: str, description: str) -> str | None:
    merged = f"{title} {description}".lower()
    if any(token in merged for token in ("meego", "symbian", "内部", "正面")):
        return "A"
    if any(token in merged for token in ("android", "开放", "联盟")):
        return "B"
    if any(token in merged for token in ("microsoft", "微软", "平台")):
        return "C"
    return None


def _resolve_slot(entry: dict[str, Any]) -> str:
    candidates = [
        entry.get("slot"),
        entry.get("intent"),
        entry.get("intent_label"),
        entry.get("scenario_intent"),
    ]
    for candidate in candidates:
        label = _normalize_label(candidate)
        if label in _SLOT_ALIASES:
            return _SLOT_ALIASES[label]

    inferred = _infer_slot_from_text(
        str(entry.get("title") or ""),
        str(entry.get("description") or ""),
    )
    if inferred:
        return inferred

    raise AmbiguousScenarioDescriptionError(
        f"unable to map scenario to deterministic slot: title={entry.get('title')!r}"
    )


def _normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for key in _DEFERRED_DYNAMIC_KEYS:
        if key in payload:
            raise DeferredScopeFeatureError(
                f"`{key}` is deferred scope in this release. "
                "Only deterministic A/B/C scenario packs are supported."
            )

    normalized = dict(payload)
    raw_scenarios = payload.get("scenarios") or []
    scenarios: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_scenarios):
        if not isinstance(raw, dict):
            raise AmbiguousScenarioDescriptionError(
                f"scenario at index {index} must be an object"
            )
        deferred = [key for key in _DEFERRED_SCENARIO_KEYS if key in raw]
        if deferred:
            raise DeferredScopeFeatureError(
                f"scenario at index {index} uses deferred dynamic authoring keys: {deferred}. "
                "Please provide deterministic scenario descriptions only."
            )
        title = str(raw.get("title") or "").strip() or f"Scenario {index + 1}"
        description = str(raw.get("description") or "").strip()
        slot = _resolve_slot(raw)
        scenarios.append(
            {
                "slot": slot,
                "title": title,
                "description": description,
            }
        )

    normalized["scenarios"] = scenarios
    return normalized


def _derive_target_outcome(slot: str, title: str, description: str) -> str:
    merged = f"{title} {description}"
    if slot == "A":
        return "在内部生态路径中提升竞争力"
    if slot == "B":
        return "在开放联盟路径中实现生存与规模"
    if slot == "C":
        return "在外部平台联盟中维持短期稳定"
    return merged[:80] if merged else "战略结果未定义"


def _derive_constraints(description: str) -> list[str]:
    lines = _normalize_lines(description)
    deduped = list(dict.fromkeys(lines))
    if deduped:
        return deduped[:3]
    return ["约束信息不足"]


def _derive_tradeoffs(slot: str) -> list[str]:
    if slot == "A":
        return ["执行速度 vs 生态完整度", "短期收益 vs 长期掌控"]
    if slot == "B":
        return ["规模扩张 vs 差异化", "平台依赖 vs 议价空间"]
    return ["短期稳定 vs 长期自主", "交易效率 vs 战略自由度"]


def _default_resistance(slot: str) -> dict[str, float]:
    values = {
        "A": (0.8, 0.7, 0.6, 0.7),
        "B": (0.5, 0.5, 0.5, 0.4),
        "C": (0.4, 0.4, 0.5, 0.3),
    }.get(slot, (0.5, 0.5, 0.5, 0.5))
    aggregate = round(sum(values) / 4.0, 3)
    return {
        "structural_conflict": values[0],
        "resource_reallocation_drag": values[1],
        "cultural_misalignment": values[2],
        "veto_node_intensity": values[3],
        "aggregate_resistance": aggregate,
    }


def compile_nl_scenarios_to_pack(payload: dict[str, Any]) -> dict[str, Any]:
    request = ScenarioCompilationRequest.model_validate(_normalize_request_payload(payload))
    slots = {scenario.slot for scenario in request.scenarios}
    missing = [slot for slot in _REQUIRED_SLOTS if slot not in slots]
    if missing:
        raise IncompleteDeterministicPackError(
            f"scenario compilation missing required slots: {missing}"
        )

    compiled_scenarios: list[dict[str, Any]] = []
    for scenario in request.scenarios:
        if len(scenario.description.strip()) < 8:
            raise AmbiguousScenarioDescriptionError(
                f"scenario slot {scenario.slot} description is too short for deterministic compilation"
            )

        compiled_scenarios.append(
            {
                "scenario_key": scenario.slot,
                "title": scenario.title,
                "target_outcome": _derive_target_outcome(
                    scenario.slot,
                    scenario.title,
                    scenario.description,
                ),
                "constraints": _derive_constraints(scenario.description),
                "dilemma_tradeoffs": _derive_tradeoffs(scenario.slot),
                "resistance_baseline": _default_resistance(scenario.slot),
            }
        )

    compiled_scenarios.sort(key=lambda item: item["scenario_key"])
    return {
        "pack_id": request.pack_id,
        "pack_version": request.pack_version,
        "scenarios": compiled_scenarios,
    }
