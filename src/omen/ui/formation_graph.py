"""Visualization helpers for strategic formation chain."""

from __future__ import annotations

import importlib
from typing import Any


def _safe_count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return len(value)
    if value is None:
        return 0
    return 1


def _build_child_labels(formation_chain: dict[str, Any]) -> dict[str, list[str]]:
    perception = formation_chain.get("perception") or []
    constraint_conflict = formation_chain.get("constraint_conflict") or {}
    mediation = formation_chain.get("mediation") or {}
    decision_logic = formation_chain.get("decision_logic") or {}
    execution_delta = formation_chain.get("execution_delta") or []

    perception_children: list[str] = []
    for item in perception:
        if not isinstance(item, dict):
            continue
        label = str(item.get("source_name") or item.get("source") or item.get("type") or "signal").strip()
        if label:
            perception_children.append(label)

    internal_constraints = constraint_conflict.get("internal_constraints") or []
    external_pressures = constraint_conflict.get("external_pressures") or []
    constraint_children = [str(item).strip() for item in internal_constraints if str(item).strip()]
    for item in external_pressures:
        if not isinstance(item, dict):
            continue
        label = str(item.get("source_name") or item.get("description") or "external_pressure").strip()
        if label:
            constraint_children.append(label)

    mediation_children: list[str] = []
    beliefs = mediation.get("core_beliefs") or []
    if beliefs:
        for belief in beliefs:
            label = str(belief).strip()
            if label:
                mediation_children.append(f"Belief: {label}")
    decision_style = str(mediation.get("decision_style") or "").strip()
    if decision_style:
        mediation_children.append(f"Style: {decision_style}")
    non_negotiables = mediation.get("non_negotiables") or []
    if non_negotiables:
        for item in non_negotiables:
            label = str(item).strip()
            if label:
                mediation_children.append(f"Constraint: {label}")

    decision_children: list[str] = []
    event_name = str(decision_logic.get("event_name") or "").strip()
    if event_name:
        decision_children.append(f"Event: {event_name}")
    strategy_id = str(decision_logic.get("strategy_id") or "").strip()
    if strategy_id:
        decision_children.append(f"Strategy: {strategy_id}")
    action_orientation = str(decision_logic.get("action_orientation") or "").strip()
    if action_orientation:
        decision_children.append(f"Action: {action_orientation}")

    execution_children: list[str] = []
    for item in execution_delta:
        if not isinstance(item, dict):
            continue
        label = str(item.get("target_name") or item.get("target") or item.get("description") or "delta").strip()
        if label:
            execution_children.append(label)

    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    return {
        "Perception": _dedupe(perception_children),
        "Constraint Conflict": _dedupe(constraint_children),
        "Mediation": _dedupe(mediation_children),
        "Decision Logic": _dedupe(decision_children),
        "Execution Delta": _dedupe(execution_children),
    }


def _child_y_positions(center_y: float, count: int, spacing: float = 0.07) -> list[float]:
    if count <= 0:
        return []
    if count == 1:
        return [center_y + 0.08]
    offset = ((count - 1) / 2.0) * spacing
    return [center_y + offset - index * spacing for index in range(count)]


def build_formation_chain_figure(payload: dict[str, Any]) -> Any:
    go = importlib.import_module("plotly.graph_objects")

    formation_chain = payload.get("formation_chain") or {}
    constraint_conflict = formation_chain.get("constraint_conflict") or {}

    perception_count = _safe_count(formation_chain.get("perception") or [])
    constraint_count = _safe_count(constraint_conflict.get("internal_constraints") or []) + _safe_count(
        constraint_conflict.get("external_pressures") or []
    )
    mediation_count = _safe_count(formation_chain.get("mediation") or {})
    decision_count = _safe_count(formation_chain.get("decision_logic") or {})
    execution_count = _safe_count(formation_chain.get("execution_delta") or [])

    labels = [
        f"Perception\n({perception_count})",
        f"Constraint Conflict\n({constraint_count})",
        f"Mediation\n({mediation_count})",
        f"Decision Logic\n({decision_count})",
        f"Execution Delta\n({execution_count})",
    ]
    stages = ["Perception", "Constraint Conflict", "Mediation", "Decision Logic", "Execution Delta"]
    child_labels = _build_child_labels(formation_chain)

    node_x = [0.05, 0.27, 0.5, 0.73, 0.95]
    node_y = [0.5, 0.5, 0.5, 0.5, 0.5]

    fig = go.Figure()

    for i in range(len(node_x) - 1):
        fig.add_trace(
            go.Scatter(
                x=[node_x[i], node_x[i + 1]],
                y=[node_y[i], node_y[i + 1]],
                mode="lines",
                line={"width": 3, "color": "#64748B"},
                hoverinfo="none",
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=labels,
            textposition="bottom center",
            marker={
                "size": [30, 34, 34, 34, 34],
                "color": ["#0EA5E9", "#F59E0B", "#8B5CF6", "#2563EB", "#10B981"],
                "line": {"width": 1, "color": "#1E293B"},
            },
            hoverinfo="text",
            hovertext=labels,
            showlegend=False,
        )
    )

    child_x: list[float] = []
    child_y: list[float] = []
    child_hover: list[str] = []
    edge_lines_x: list[float | None] = []
    edge_lines_y: list[float | None] = []
    child_annotations: list[dict[str, Any]] = []

    for idx, stage in enumerate(stages):
        stage_children = child_labels.get(stage) or []
        if not stage_children:
            continue

        y_slots = _child_y_positions(node_y[idx], len(stage_children))
        for child_idx, label in enumerate(stage_children):
            child_node_x = node_x[idx]
            child_node_y = y_slots[child_idx]

            child_x.append(child_node_x)
            child_y.append(child_node_y)
            child_hover.append(f"{stage}: {label}")
            child_annotations.append(
                {
                    "x": child_node_x,
                    "y": child_node_y,
                    "xref": "x",
                    "yref": "y",
                    "text": label,
                    "showarrow": False,
                    "xshift": 18,
                    "yshift": 10 if child_node_y >= node_y[idx] else -10,
                    "xanchor": "left",
                    "font": {"size": 11, "color": "#334155"},
                    "align": "left",
                }
            )

            edge_lines_x.extend([node_x[idx], child_node_x, None])
            edge_lines_y.extend([node_y[idx], child_node_y, None])

    if edge_lines_x:
        fig.add_trace(
            go.Scatter(
                x=edge_lines_x,
                y=edge_lines_y,
                mode="lines",
                line={"width": 1.2, "color": "#CBD5E1"},
                hoverinfo="none",
                showlegend=False,
            )
        )

    if child_x:
        fig.add_trace(
            go.Scatter(
                x=child_x,
                y=child_y,
                mode="markers",
                marker={
                    "size": 14,
                    "color": "#E2E8F0",
                    "line": {"width": 1, "color": "#94A3B8"},
                },
                hoverinfo="text",
                hovertext=child_hover,
                showlegend=False,
            )
        )

    for i in range(len(node_x) - 1):
        fig.add_annotation(
            x=node_x[i + 1] - 0.03,
            y=node_y[i + 1],
            ax=node_x[i] + 0.03,
            ay=node_y[i],
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.5,
            arrowcolor="#475569",
            text="",
        )

    founder = str((payload.get("summary") or {}).get("founder") or "Founder")
    fig.update_layout(
        title=f"Strategic Formation Closed Loop · {founder}",
        showlegend=False,
        xaxis={"visible": False, "range": [0, 1]},
        yaxis={
            "visible": False,
            "range": [
                min([0.28, *child_y]) - 0.05 if child_y else 0.28,
                max([0.72, *child_y]) + 0.05 if child_y else 0.72,
            ],
        },
        margin={"l": 20, "r": 20, "t": 70, "b": 20},
        plot_bgcolor="white",
        paper_bgcolor="white",
        annotations=child_annotations,
    )

    return fig
