"""Scenario condition-set generation helpers."""

from __future__ import annotations

from typing import Any


def generate_condition_sets(
    *,
    scenario_key: str,
    resistance_baseline: dict[str, Any],
) -> dict[str, Any]:
    required = [
        "明确董事会授权范围",
        "指定单一责任人负责关键路径推进",
    ]

    warning: list[str] = []
    if float(resistance_baseline.get("resource_reallocation_drag", 0.0)) >= 0.6:
        warning.append("资源重分配阻力较高，需准备阶段性缓冲计划")
    if float(resistance_baseline.get("cultural_misalignment", 0.0)) >= 0.6:
        warning.append("组织文化错位明显，需先完成关键团队对齐")

    blocking: list[str] = []
    if float(resistance_baseline.get("veto_node_intensity", 0.0)) >= 0.8:
        blocking.append("关键否决节点阻力过高，需先移除组织阻断")

    if scenario_key == "A":
        required.append("确保内部平台核心能力具备连续投入")
    elif scenario_key == "B":
        required.append("建立外部生态合作中的差异化保护机制")
    elif scenario_key == "C":
        required.append("设置外部平台依赖的退出与切换条件")

    if not warning:
        warning.append("持续监控跨团队协同摩擦并每周复盘")

    return {
        "required": required,
        "warning": warning,
        "blocking": blocking,
    }


def build_condition_derivation_trace(
    *,
    scenario_key: str,
    scenario_ontology: dict[str, Any],
    selected_dimensions: dict[str, Any],
    strategic_conditions: dict[str, Any],
) -> dict[str, Any]:
    objective = str(scenario_ontology.get("objective") or "").strip()
    constraints = list(scenario_ontology.get("constraints") or [])
    selected = list(selected_dimensions.get("selected_dimension_keys") or [])
    required = list(strategic_conditions.get("required") or [])

    steps = [
        f"Scenario objective identified: {objective or 'unknown objective'}",
        f"Key constraints interpreted: {', '.join(constraints[:2]) if constraints else 'none'}",
        f"Selected dimensions: {', '.join(selected) if selected else 'none'}",
        f"Condition projection produced required actions: {', '.join(required[:2]) if required else 'none'}",
    ]

    return {
        "scenario_key": scenario_key,
        "ontology_refs": [
            "objective",
            "constraints",
            "tradeoff_pressure",
            "resistance_assumptions",
        ],
        "selected_dimensions": selected,
        "derivation_steps": steps,
        "missing_evidence_reasons": [],
    }
