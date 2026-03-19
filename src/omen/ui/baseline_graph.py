"""Plot builders for Spec 6 baseline path visualization."""

from __future__ import annotations

import importlib
from typing import Any

import networkx as nx


def _build_curve_points(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    bend: float,
    samples: int = 24,
) -> tuple[list[float], list[float]]:
    control_x = (start_x + end_x) / 2 + bend * (end_y - start_y)
    control_y = (start_y + end_y) / 2 - bend * (end_x - start_x)

    curve_x: list[float] = []
    curve_y: list[float] = []
    for index in range(samples + 1):
        t = index / samples
        one_minus_t = 1 - t
        curve_x.append(
            (one_minus_t * one_minus_t * start_x)
            + (2 * one_minus_t * t * control_x)
            + (t * t * end_x)
        )
        curve_y.append(
            (one_minus_t * one_minus_t * start_y)
            + (2 * one_minus_t * t * control_y)
            + (t * t * end_y)
        )
    return curve_x, curve_y


def _weighted_edge_trace(
    *,
    go: Any,
    positions: dict[str, Any],
    source: str,
    target: str,
    weight: float,
    color: str,
    dash: str,
    name: str,
    showlegend: bool,
    bend: float,
    hover_label: str,
) -> Any:
    x0, y0 = positions[source]
    x1, y1 = positions[target]
    curve_x, curve_y = _build_curve_points(x0, y0, x1, y1, bend, samples=18)
    line_width = 1.1 + max(0.0, min(1.0, weight)) * 5.2
    return go.Scatter(
        x=curve_x,
        y=curve_y,
        line={"width": line_width, "color": color, "dash": dash},
        hoverinfo="text",
        hovertext=[hover_label] * len(curve_x),
        mode="lines",
        name=name,
        showlegend=showlegend,
    )


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
    for edge in view_model.get("graph_edges", []):
        graph.add_edge(edge["source"], edge["target"])

    if not graph.nodes:
        fig = go.Figure()
        fig.update_layout(title="No baseline path available")
        return fig

    positions = nx.spring_layout(graph, seed=42)

    transition_map = {
        str(item.get("transition_id") or ""): item
        for item in list(view_model.get("weighted_transitions") or [])
    }

    model_edge_traces: list[Any] = []
    adjusted_edge_traces: list[Any] = []
    model_legend_shown = False
    adjusted_legend_shown = False
    for edge in view_model.get("graph_edges", []):
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if not source or not target:
            continue
        if source not in positions or target not in positions:
            continue

        transition_id = f"transition:{source}->{target}"
        transition = transition_map.get(transition_id, {})
        baseline_weight = float(transition.get("baseline_weight") or 0.5)
        adjusted_weight = float(transition.get("adjusted_weight") or baseline_weight)

        model_edge_traces.append(
            _weighted_edge_trace(
                go=go,
                positions=positions,
                source=source,
                target=target,
                weight=baseline_weight,
                color="#94A3B8",
                dash="dash",
                name="Baseline transition",
                showlegend=not model_legend_shown,
                bend=0.02,
                hover_label=f"{source} -> {target} | baseline_weight={baseline_weight:.3f}",
            )
        )
        model_legend_shown = True

        adjusted_edge_traces.append(
            _weighted_edge_trace(
                go=go,
                positions=positions,
                source=source,
                target=target,
                weight=adjusted_weight,
                color="#0F766E",
                dash="solid",
                name="Adjusted transition",
                showlegend=not adjusted_legend_shown,
                bend=-0.06,
                hover_label=f"{source} -> {target} | adjusted_weight={adjusted_weight:.3f}",
            )
        )
        adjusted_legend_shown = True

    model_node_x: list[float] = []
    model_node_y: list[float] = []
    model_labels: list[str] = []
    model_hover_texts: list[str] = []
    model_marker_colors: list[str] = []
    for node_id in graph.nodes():
        x, y = positions[node_id]
        label = graph.nodes[node_id].get("label", node_id)
        summary = graph.nodes[node_id].get("summary", node_id)
        event = graph.nodes[node_id].get("event", "Stable progression")
        model_node_x.append(x)
        model_node_y.append(y)
        model_labels.append(label)
        model_hover_texts.append(summary)
        model_marker_colors.append(event_color_map.get(event, "#2563EB"))

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
    fig = go.Figure(data=[*model_edge_traces, *adjusted_edge_traces, model_node_trace])
    fig.update_layout(
        title="Baseline Evolution Path",
        showlegend=True,
        legend={"orientation": "h", "x": 0.0, "y": 1.08},
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig
