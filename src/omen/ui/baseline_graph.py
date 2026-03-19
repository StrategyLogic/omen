"""Plot builders for Spec 6 baseline path visualization."""

from __future__ import annotations

import importlib
from typing import Any

import networkx as nx


def build_baseline_path_figure(view_model: dict) -> Any:
    go = importlib.import_module("plotly.graph_objects")

    event_color_map = {
        "User overlap emerges": "#EA580C",
        "Competition activated": "#DC2626",
        "Leader shift": "#7C3AED",
        "Competition expands": "#D97706",
        "Overlap intensifies": "#2563EB",
        "Stable progression": "#2563EB",
    }

    graph = nx.DiGraph()
    for node in view_model.get("graph_nodes", []):
        graph.add_node(
            node["id"],
            label=node.get("label", node["id"]),
            summary=node.get("summary", node.get("label", node["id"])),
            event=node.get("event", "Stable progression"),
        )
    for node in view_model.get("reality_graph_nodes", []):
        graph.add_node(
            node["id"],
            label=node.get("label", node["id"]),
            summary=node.get("summary", node.get("label", node["id"])),
            event=node.get("event", "Reality divergence"),
        )
    for edge in view_model.get("graph_edges", []):
        graph.add_edge(edge["source"], edge["target"])
    reality_edges = view_model.get("reality_graph_edges", [])
    for edge in reality_edges:
        source = edge.get("source")
        target = edge.get("target")
        if source and target:
            graph.add_edge(source, target)

    if not graph.nodes:
        fig = go.Figure()
        fig.update_layout(title="No baseline path available")
        return fig

    positions = nx.spring_layout(graph, seed=42)

    reality_edge_pairs = {
        (str(edge.get("source") or ""), str(edge.get("target") or ""))
        for edge in reality_edges
    }

    model_edge_x: list[float | None] = []
    model_edge_y: list[float | None] = []
    for edge in view_model.get("graph_edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        if (str(source), str(target)) in reality_edge_pairs:
            continue
        if source not in positions or target not in positions:
            continue
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        model_edge_x.extend([x0, x1, None])
        model_edge_y.extend([y0, y1, None])

    reality_edge_x: list[float | None] = []
    reality_edge_y: list[float | None] = []
    for edge in reality_edges:
        source = edge.get("source")
        target = edge.get("target")
        if source not in positions or target not in positions:
            continue
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        reality_edge_x.extend([x0, x1, None])
        reality_edge_y.extend([y0, y1, None])

    model_node_x: list[float] = []
    model_node_y: list[float] = []
    model_labels: list[str] = []
    model_hover_texts: list[str] = []
    model_marker_colors: list[str] = []
    reality_node_x: list[float] = []
    reality_node_y: list[float] = []
    reality_labels: list[str] = []
    reality_hover_texts: list[str] = []
    reality_node_ids = {
        str(edge.get("source") or "") for edge in reality_edges
    } | {
        str(edge.get("target") or "") for edge in reality_edges
    }
    for node_id in graph.nodes():
        x, y = positions[node_id]
        label = graph.nodes[node_id].get("label", node_id)
        summary = graph.nodes[node_id].get("summary", node_id)
        event = graph.nodes[node_id].get("event", "Stable progression")
        if node_id in reality_node_ids:
            reality_node_x.append(x)
            reality_node_y.append(y)
            reality_labels.append(label)
            reality_hover_texts.append(summary)
        else:
            model_node_x.append(x)
            model_node_y.append(y)
            model_labels.append(label)
            model_hover_texts.append(summary)
            model_marker_colors.append(event_color_map.get(event, "#2563EB"))

    model_edge_trace = go.Scatter(
        x=model_edge_x,
        y=model_edge_y,
        line={"width": 1.6, "color": "#94A3B8", "dash": "dash"},
        hoverinfo="none",
        mode="lines",
        name="Model path",
    )

    reality_edge_trace = go.Scatter(
        x=reality_edge_x,
        y=reality_edge_y,
        line={"width": 3.0, "color": "#DC2626"},
        hoverinfo="none",
        mode="lines",
        name="Real-world path",
    )

    model_node_trace = go.Scatter(
        x=model_node_x,
        y=model_node_y,
        mode="markers+text",
        text=model_labels,
        textposition="top center",
        hovertext=model_hover_texts,
        hoverinfo="text",
        marker={"size": 16, "color": model_marker_colors, "line": {"width": 1, "color": "#1E3A8A"}},
        name="Model nodes",
    )

    reality_node_trace = go.Scatter(
        x=reality_node_x,
        y=reality_node_y,
        mode="markers+text",
        text=reality_labels,
        textposition="top center",
        hovertext=reality_hover_texts,
        hoverinfo="text",
        marker={"size": 16, "color": "#DC2626", "line": {"width": 1, "color": "#7F1D1D"}},
        name="Real-world nodes",
    )

    fig = go.Figure(data=[model_edge_trace, reality_edge_trace, model_node_trace, reality_node_trace])
    fig.update_layout(
        title="Baseline Evolution Path",
        showlegend=True,
        legend={"orientation": "h", "x": 0.0, "y": 1.08},
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig
