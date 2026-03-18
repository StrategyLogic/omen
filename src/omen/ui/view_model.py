"""View model builders for Spec 6 case replay UI."""

from __future__ import annotations

from typing import Any


def _build_graph_nodes(result: dict[str, Any]) -> list[dict[str, Any]]:
    timeline = result.get("timeline", [])
    nodes: list[dict[str, Any]] = []
    for snapshot in timeline:
        step = snapshot.get("step")
        nodes.append(
            {
                "id": f"step-{step}",
                "label": f"Step {step}",
                "kind": "phase",
                "evidence_level": "medium",
            }
        )
    return nodes


def _build_graph_edges(result: dict[str, Any]) -> list[dict[str, Any]]:
    timeline = result.get("timeline", [])
    edges: list[dict[str, Any]] = []
    previous = None
    for snapshot in timeline:
        current = f"step-{snapshot.get('step')}"
        if previous is not None:
            edges.append({"id": f"{previous}->{current}", "source": previous, "target": current})
        previous = current
    return edges


def build_case_replay_view_model(
    *,
    result: dict[str, Any],
    explanation: dict[str, Any],
    case_id: str,
) -> dict[str, Any]:
    nodes = _build_graph_nodes(result)
    edges = _build_graph_edges(result)

    branch_points = explanation.get("branch_points", [])
    causal_options: list[dict[str, Any]] = []
    for index, point in enumerate(branch_points, start=1):
        step = point.get("step")
        causal_options.append(
            {
                "trace_id": f"trace-{index}",
                "target_node_id": f"step-{step}" if step is not None else "step-0",
                "highlight_group_id": f"highlight-{index}",
                "summary": point.get("description", "branch point"),
                "uncertainty_note": None,
            }
        )

    editable_controls = [
        {
            "control_id": "user_overlap_threshold",
            "label": "User overlap threshold",
            "control_type": "parameter",
            "current_value": 0.2,
            "allowed_values": [0.1, 0.2, 0.3, 0.4, 0.5],
            "source_node_id": "step-1",
        }
    ]

    evidence_panel = [
        {
            "node_id": f"step-{point.get('step')}",
            "evidence_level": "medium",
            "summary": point.get("description", "branch point evidence"),
            "source_refs": [],
        }
        for point in branch_points
        if point.get("step") is not None
    ]

    return {
        "case_id": case_id,
        "baseline_summary": {
            "outcome": result.get("outcome_class", "unknown"),
            "phase_count": len(result.get("timeline", [])),
            "node_count": len(nodes),
            "summary_text": explanation.get("narrative_summary", ""),
        },
        "graph_nodes": nodes,
        "graph_edges": edges,
        "causal_trace_options": causal_options,
        "editable_controls": editable_controls,
        "evidence_panel": evidence_panel,
    }
