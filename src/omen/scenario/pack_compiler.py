"""Compile natural language scenario descriptions into deterministic scenario packs."""

from __future__ import annotations

from typing import Any

from omen.scenario.ingest_validator import (
    AmbiguousScenarioDescriptionError,
    IncompleteDeterministicPackError,
)
from omen.scenario.ontology_models import ScenarioCompilationRequest

_REQUIRED_SLOTS = ("A", "B", "C")


def _normalize_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    return [line for line in lines if line]


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
    if lines:
        return lines[:3]
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
    request = ScenarioCompilationRequest.model_validate(payload)
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
