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
        yaxis={"visible": False, "range": [0.3, 0.7]},
        margin={"l": 20, "r": 20, "t": 70, "b": 20},
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    return fig
