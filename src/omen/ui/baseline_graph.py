"""Plot builders for Spec 6 baseline path visualization."""

from __future__ import annotations

import importlib
from typing import Any

import networkx as nx


def build_baseline_path_figure(view_model: dict) -> Any:
    go = importlib.import_module("plotly.graph_objects")

    graph = nx.DiGraph()
    for node in view_model.get("graph_nodes", []):
        graph.add_node(node["id"], label=node.get("label", node["id"]))
    for edge in view_model.get("graph_edges", []):
        graph.add_edge(edge["source"], edge["target"])

    if not graph.nodes:
        fig = go.Figure()
        fig.update_layout(title="No baseline path available")
        return fig

    positions = nx.spring_layout(graph, seed=42)

    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    node_x: list[float] = []
    node_y: list[float] = []
    labels: list[str] = []
    for node_id in graph.nodes():
        x, y = positions[node_id]
        node_x.append(x)
        node_y.append(y)
        labels.append(graph.nodes[node_id].get("label", node_id))

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line={"width": 1.2, "color": "#94A3B8"},
        hoverinfo="none",
        mode="lines",
        name="transitions",
    )

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=labels,
        textposition="top center",
        hoverinfo="text",
        marker={"size": 16, "color": "#2563EB", "line": {"width": 1, "color": "#1E3A8A"}},
        name="steps",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title="Baseline Evolution Path",
        showlegend=False,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig
