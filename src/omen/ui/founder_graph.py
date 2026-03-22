"""Founder graph visualization helpers for analysis status view."""

from __future__ import annotations
import importlib
from typing import Any
import networkx as nx


def _parse_edge_curvature(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        pass

    lower = text.lower()
    if "rad=" in lower:
        try:
            tail = lower.split("rad=", 1)[1]
            token = tail.split(",", 1)[0].strip()
            return float(token)
        except ValueError:
            return 0.0
    return 0.0


def _curved_edge_points(x0: float, y0: float, x1: float, y1: float, curvature: float) -> tuple[list[float], list[float]]:
    if abs(curvature) < 1e-9:
        return [x0, x1], [y0, y1]

    mid_x = (x0 + x1) / 2.0
    mid_y = (y0 + y1) / 2.0
    dx = x1 - x0
    dy = y1 - y0
    norm = (dx**2 + dy**2) ** 0.5 or 1.0
    perp_x = -dy / norm
    perp_y = dx / norm
    control_x = mid_x + perp_x * curvature
    control_y = mid_y + perp_y * curvature

    points = 20
    xs: list[float] = []
    ys: list[float] = []
    for i in range(points + 1):
        t = i / points
        one_minus_t = 1.0 - t
        x = (one_minus_t**2) * x0 + 2 * one_minus_t * t * control_x + (t**2) * x1
        y = (one_minus_t**2) * y0 + 2 * one_minus_t * t * control_y + (t**2) * y1
        xs.append(x)
        ys.append(y)
    return xs, ys

def build_founder_graph_figure(payload: dict[str, Any]) -> Any:
    go = importlib.import_module("plotly.graph_objects")

    graph = nx.MultiDiGraph()
    founder_graph = payload.get("founder_graph") or {}
    nodes = founder_graph.get("nodes") or []
    edges = founder_graph.get("edges") or []

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            continue
        graph.add_node(
            node_id,
            label=str(node.get("label") or node_id),
            node_type=str(node.get("node_type") or "other"),
        )

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = str(edge.get("source") or "").strip()
        target = str(edge.get("target") or "").strip()
        if not source or not target or source not in graph or target not in graph:
            continue
        graph.add_edge(
            source,
            target,
            label=str(edge.get("label") or ""),
            curvature=("arc3,rad=0.05"),
        )

    fig = go.Figure()
    if not graph.nodes:
        fig.update_layout(title="Founder Graph (empty)")
        return fig

    positions = nx.kamada_kawai_layout(graph)

    edge_traces: list[Any] = []
    edge_label_x: list[float] = []
    edge_label_y: list[float] = []
    edge_labels: list[str] = []
    for source, target, data in graph.edges(data=True):
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        curvature = _parse_edge_curvature(data.get("curvature"))
        curve_x, curve_y = _curved_edge_points(x0, y0, x1, y1, curvature)
        edge_traces.append(
            go.Scatter(
                x=curve_x,
                y=curve_y,
                mode="lines",
                line={"width": 1, "color": "#94A3B8"},
                hoverinfo="none",
                showlegend=False,
                name="relations",
            )
        )
        edge_label_x.append(curve_x[len(curve_x) // 2])
        edge_label_y.append(curve_y[len(curve_y) // 2])
        edge_labels.append(str(data.get("label") or ""))

    node_x: list[float] = []
    node_y: list[float] = []
    node_text: list[str] = []
    node_colors: list[str] = []
    color_map = {
        "founder_actor": "#DC2626",
        "actor": "#059669",
        "event": "#2563EB",
        "constraint": "#D97706",
    }

    for node_id, data in graph.nodes(data=True):
        x, y = positions[node_id]
        node_x.append(x)
        node_y.append(y)
        node_text.append(str(data.get("label") or node_id))
        node_colors.append(color_map.get(str(data.get("node_type") or ""), "#64748B"))

    for trace in edge_traces:
        fig.add_trace(trace)
    fig.add_trace(
        go.Scatter(
            x=edge_label_x,
            y=edge_label_y,
            mode="text",
            text=edge_labels,
            textposition="middle center",
            hoverinfo="none",
            textfont={"size": 10, "color": "#334155"},
            name="relation_labels",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_text,
            textposition="top center",
            marker={"size": 16, "color": node_colors, "line": {"width": 1, "color": "#1E293B"}},
            hoverinfo="text",
            name="nodes",
        )
    )

    fig.update_layout(
        title="Founder Graph",
        showlegend=False,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig
