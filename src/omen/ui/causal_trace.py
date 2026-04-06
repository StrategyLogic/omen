"""Helpers for linking causal traces with reality gaps in UI."""

from __future__ import annotations

from typing import Any


def _choose_target_node_id(
    gap: dict[str, Any],
    branch_points: list[dict[str, Any]],
    graph_nodes: list[dict[str, Any]],
    fallback_index: int,
) -> str:
    factor = str(gap.get("factor") or "").strip()
    preferred_types = {
        "simulated_vs_real_outcome": ["winner_emergence", "competition_activation"],
        "adoption_resistance": ["competition_activation", "user_overlap"],
        "pilot_success_to_scale": ["winner_emergence", "competition_activation"],
    }.get(factor, [])

    for preferred_type in preferred_types:
        for point in branch_points:
            if point.get("type") == preferred_type and point.get("step") is not None:
                return f"step-{point.get('step')}"

    if factor == "simulated_vs_real_outcome" and graph_nodes:
        return str(graph_nodes[-1].get("id") or "step-0")

    for point in branch_points:
        if point.get("step") is not None:
            return f"step-{point.get('step')}"

    if graph_nodes:
        return str(graph_nodes[min(fallback_index, len(graph_nodes) - 1)].get("id") or "step-0")
    return "step-0"


def build_causal_gap_links(
    branch_points: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    graph_nodes: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    node_list = graph_nodes or []
    if not gaps:
        return links

    for index, gap in enumerate(gaps, start=1):
        target_node_id = _choose_target_node_id(gap, branch_points, node_list, index - 1)
        trace_type = "branch_point"
        if target_node_id.startswith("step-"):
            step_value = target_node_id.rsplit("step-", maxsplit=1)[-1]
            for point in branch_points:
                if str(point.get("step")) == step_value:
                    trace_type = str(point.get("type") or "branch_point")
                    break
        links.append(
            {
                "gap_id": gap.get("gap_id", f"gap-{index}"),
                "trace_type": trace_type,
                "target_node_id": target_node_id,
                "summary": gap.get("factor", "reality gap"),
            }
        )

    return links
