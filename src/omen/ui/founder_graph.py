"""Founder graph visualization helpers for analysis status view."""

from __future__ import annotations
import importlib
from typing import Any
import networkx as nx


def build_founder_graph_figure(payload: dict[str, Any]) -> Any:
    go = importlib.import_module("plotly.graph_objects")

    graph = nx.DiGraph()
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
        edge_traces.append(
            go.Scatter(
                x=([x0, x1, None]),
                y=([y0, y1, None]),
                mode="lines",
                line={"width": 1, "color": "#94A3B8"},
                hoverinfo="none",
                showlegend=False,
                name="relations",
            )
        )
        edge_label_x.append((x0 + x1) / 2)
        edge_label_y.append((y0 + y1) / 2)
        edge_labels.append(str(data.get("label") or ""))

    node_x: list[float] = []
    node_y: list[float] = []
    node_text: list[str] = []
    node_colors: list[str] = []
    color_map = {
        "founder_actor": "#DC2626",
        "actor": "#059669",
        "customer": "#0891B2", 
        "competitor": "#EA580C", 
        "product": "#7C3AED",
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
