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


def _overlay_endpoint(
    source_x: float,
    source_y: float,
    slot: int,
    direction: int,
) -> tuple[float, float, float]:
    horizontal = 0.28 + 0.06 * (slot % 2)
    vertical = (0.14 + 0.11 * slot) * direction
    bend = 0.22 * direction
    return source_x + horizontal, source_y + vertical, bend


def _overlay_traces(
    *,
    go: Any,
    positions: dict[str, tuple[float, float]],
    overlays: list[dict[str, Any]],
    color: str,
    legend_name: str,
    direction: int,
) -> tuple[list[Any], list[dict[str, float | str]]]:
    traces: list[Any] = []
    labels: list[dict[str, float | str]] = []
    source_counts: dict[str, int] = {}

    for index, overlay in enumerate(overlays):
        source_node_id = str(overlay.get("source_node_id") or "")
        if source_node_id not in positions:
            continue

        slot = source_counts.get(source_node_id, 0)
        source_counts[source_node_id] = slot + 1

        start_x, start_y = positions[source_node_id]
        end_x, end_y, bend = _overlay_endpoint(start_x, start_y, slot, direction)
        curve_x, curve_y = _build_curve_points(start_x, start_y, end_x, end_y, bend)

        traces.append(
            go.Scatter(
                x=curve_x,
                y=curve_y,
                line={"width": 2.0, "color": color},
                hoverinfo="text",
                hovertext=[str(overlay.get("label") or "")] * len(curve_x),
                mode="lines",
                name=legend_name,
                showlegend=index == 0,
            )
        )
        labels.append(
            {
                "x": end_x,
                "y": end_y,
                "label": str(overlay.get("label") or ""),
                "ax": curve_x[-2],
                "ay": curve_y[-2],
                "color": color,
            }
        )

    return traces, labels


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

    model_edge_x: list[float | None] = []
    model_edge_y: list[float | None] = []
    for edge in view_model.get("graph_edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        if source not in positions or target not in positions:
            continue
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        model_edge_x.extend([x0, x1, None])
        model_edge_y.extend([y0, y1, None])

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

    model_edge_trace = go.Scatter(
        x=model_edge_x,
        y=model_edge_y,
        line={"width": 1.6, "color": "#94A3B8", "dash": "dash"},
        hoverinfo="none",
        mode="lines",
        name="Model path",
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

    gap_traces, gap_labels = _overlay_traces(
        go=go,
        positions=positions,
        overlays=list(view_model.get("gap_overlays") or []),
        color="#475569",
        legend_name="Reality gaps",
        direction=1,
    )

    control_traces, control_labels = _overlay_traces(
        go=go,
        positions=positions,
        overlays=list(view_model.get("control_overlays") or []),
        color="#B91C1C",
        legend_name="Control points",
        direction=-1,
    )

    fig = go.Figure(data=[model_edge_trace, model_node_trace, *gap_traces, *control_traces])
    for item in [*gap_labels, *control_labels]:
        fig.add_annotation(
            x=item["x"],
            y=item["y"],
            ax=item["ax"],
            ay=item["ay"],
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            text=str(item["label"]),
            showarrow=True,
            arrowhead=2,
            arrowsize=1.1,
            arrowwidth=1.8,
            arrowcolor=str(item["color"]),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#CBD5E1",
            borderwidth=1,
        )
    fig.update_layout(
        title="Baseline Evolution Path",
        showlegend=True,
        legend={"orientation": "h", "x": 0.0, "y": 1.08},
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig
