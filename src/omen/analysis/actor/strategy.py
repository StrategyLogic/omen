"""Strategic freedom scoring and condition-set generation."""

from __future__ import annotations

from typing import Any


def calculate_strategic_freedom_factor(
    *,
    capability_fit: str,
    resistance_baseline: dict[str, Any],
) -> float:
    fit_base = {
        "high": 0.8,
        "medium": 0.55,
        "low": 0.3,
    }.get(str(capability_fit).strip().lower(), 0.5)

    resistance = float(resistance_baseline.get("aggregate_resistance", 0.5))
    score = fit_base * 0.7 + (1.0 - resistance) * 0.3
    return round(max(0.0, min(1.0, score)), 3)


def generate_condition_sets(
    *,
    scenario_key: str,
    strategic_freedom_score: float,
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
    if strategic_freedom_score < 0.35:
        blocking.append("战略自由度过低，当前路径不可执行")
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
        "score": round(max(0.0, min(1.0, strategic_freedom_score)), 3),
        "required": required,
        "warning": warning,
        "blocking": blocking,
    }
