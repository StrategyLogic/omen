"""Ontology graph visualization helpers for Spec 6 UI."""

from __future__ import annotations

import importlib
from typing import Any

import networkx as nx


def _extract_concepts(tbox: dict[str, Any]) -> list[dict[str, str]]:
    concepts = tbox.get("concepts")
    extracted: list[dict[str, str]] = []
    if not isinstance(concepts, list):
        return extracted

    for item in concepts:
        if isinstance(item, str):
            name = item.strip()
            if name:
                extracted.append({"name": name, "category": "other"})
            continue
        if isinstance(item, dict) and "name" in item:
            name = str(item.get("name") or "").strip()
            if name:
                extracted.append({"name": name, "category": str(item.get("category") or "other")})
            continue
        if not isinstance(item, dict):
            continue
        for _, values in item.items():
            if not isinstance(values, list):
                continue
            for child in values:
                if not isinstance(child, dict):
                    continue
                name = str(child.get("name") or child.get("id") or "").strip()
                if name:
                    extracted.append({"name": name, "category": "other"})
    return extracted


def _extract_actor_ids(actor_items: Any) -> set[str]:
    if not isinstance(actor_items, list):
        return set()

    actor_ids: set[str] = set()
    for item in actor_items:
        if isinstance(item, str):
            value = item.strip()
            if value:
                actor_ids.add(value)
            continue
        if isinstance(item, dict):
            actor_id = str(item.get("actor_id") or item.get("id") or item.get("name") or "").strip()
            if actor_id:
                actor_ids.add(actor_id)
    return actor_ids


def _build_graph(payload: dict[str, Any]) -> nx.DiGraph:
    graph = nx.DiGraph()

    tbox = payload.get("tbox") if isinstance(payload.get("tbox"), dict) else {}
    abox = payload.get("abox") if isinstance(payload.get("abox"), dict) else {}

    concepts = _extract_concepts(tbox)
    concept_names = {item["name"] for item in concepts}
    for concept in concepts:
        node_id = f"concept:{concept['name']}"
        graph.add_node(node_id, label=concept["name"], node_type="concept", category=concept["category"])

    relations = tbox.get("relations") if isinstance(tbox.get("relations"), list) else []
    for relation in relations:
        if not isinstance(relation, dict):
            continue
        name = str(relation.get("name") or relation.get("relation") or "").strip()
        source = str(relation.get("source") or "").strip()
        target = str(relation.get("target") or "").strip()
        if not source or not target:
            continue
        source_id = f"concept:{source}"
        target_id = f"concept:{target}"
        if source not in concept_names:
            graph.add_node(source_id, label=source, node_type="concept", category="other")
        if target not in concept_names:
            graph.add_node(target_id, label=target, node_type="concept", category="other")
        graph.add_edge(source_id, target_id, label=name or "relation")

    actors = abox.get("actors") if isinstance(abox.get("actors"), list) else []
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        actor_id = str(actor.get("actor_id") or actor.get("id") or "").strip()
        if not actor_id:
            continue
        actor_label = str(actor.get("name") or actor_id)
        actor_node_id = f"actor:{actor_id}"
        graph.add_node(actor_node_id, label=actor_label, node_type="actor", category="actor_instance")

        actor_type = str(actor.get("actor_type") or actor.get("concept") or "").strip()
        if actor_type:
            concept_node_id = f"concept:{actor_type}"
            if actor_type not in concept_names:
                graph.add_node(concept_node_id, label=actor_type, node_type="concept", category="actor")
            graph.add_edge(actor_node_id, concept_node_id, label="instance_of")

    capabilities = abox.get("capabilities") if isinstance(abox.get("capabilities"), list) else []
    for capability in capabilities:
        if not isinstance(capability, dict):
            continue
        actor_id = str(capability.get("actor_id") or "").strip()
        capability_name = str(capability.get("name") or "").strip()
        if not actor_id or not capability_name:
            continue

        actor_node_id = f"actor:{actor_id}"
        capability_node_id = f"concept:{capability_name}"
        if capability_name not in concept_names:
            graph.add_node(capability_node_id, label=capability_name, node_type="capability", category="capability")
        graph.add_edge(actor_node_id, capability_node_id, label="has_capability")

    return graph


def _seed_actor_nodes(payload: dict[str, Any], actor_scope: str) -> set[str]:
    if actor_scope not in {"tech", "market"}:
        return set()

    scope_key = "tech_space_ontology" if actor_scope == "tech" else "market_space_ontology"
    scope_payload = payload.get(scope_key) if isinstance(payload.get(scope_key), dict) else {}
    actor_ids = _extract_actor_ids(scope_payload.get("actors"))
    return {f"actor:{actor_id}" for actor_id in actor_ids if actor_id}


def _collect_reachable_with_actor_terminals(
    graph: nx.DiGraph,
    seed_nodes: set[str],
) -> set[str]:
    if not seed_nodes:
        return set()

    undirected = graph.to_undirected()
    visited: set[str] = set(seed_nodes)
    queue: list[str] = list(seed_nodes)

    while queue:
        current = queue.pop(0)
        current_data = graph.nodes[current]
        current_is_actor = str(current_data.get("node_type") or "") == "actor"
        current_is_seed = current in seed_nodes

        if current_is_actor and not current_is_seed:
            continue

        for neighbor in undirected.neighbors(current):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append(neighbor)

    return visited


def _filter_graph_by_actor_scope(graph: nx.DiGraph, payload: dict[str, Any], actor_scope: str) -> nx.DiGraph:
    if actor_scope == "all":
        return graph.copy()
    else:
        seed_nodes = {node for node in _seed_actor_nodes(payload, actor_scope) if node in graph}
        if not seed_nodes:
            filtered = graph.copy()
        else:
            reachable_nodes = _collect_reachable_with_actor_terminals(graph, seed_nodes)
            filtered = graph.subgraph(reachable_nodes).copy()
    return filtered


def build_ontology_graph_figure(payload: dict[str, Any], actor_scope: str = "all") -> Any:
    go = importlib.import_module("plotly.graph_objects")

    graph = _build_graph(payload)
    graph = _filter_graph_by_actor_scope(graph, payload, actor_scope)

    if not graph.nodes:
        fig = go.Figure()
        fig.update_layout(title="Ontology Graph (empty after filter)")
        return fig

    positions = nx.spring_layout(graph, seed=42)

    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    edge_labels: list[str] = []
    edge_label_x: list[float] = []
    edge_label_y: list[float] = []
    for source, target, data in graph.edges(data=True):
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_label_x.append((x0 + x1) / 2)
        edge_label_y.append((y0 + y1) / 2)
        edge_labels.append(str(data.get("label") or ""))

    node_x: list[float] = []
    node_y: list[float] = []
    node_text: list[str] = []
    node_colors: list[str] = []
    color_map = {
        "concept": "#2563EB",
        "actor": "#059669",
        "capability": "#D97706",
    }
    for node_id, data in graph.nodes(data=True):
        x, y = positions[node_id]
        node_x.append(x)
        node_y.append(y)
        node_text.append(str(data.get("label") or node_id))
        node_colors.append(color_map.get(str(data.get("node_type")), "#64748B"))

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line={"width": 1, "color": "#94A3B8"},
        hoverinfo="none",
        name="relations",
    )

    edge_label_trace = go.Scatter(
        x=edge_label_x,
        y=edge_label_y,
        mode="text",
        text=edge_labels,
        textposition="middle center",
        hoverinfo="none",
        textfont={"size": 10, "color": "#334155"},
        name="relation_labels",
    )

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        marker={"size": 16, "color": node_colors, "line": {"width": 1, "color": "#1E293B"}},
        hoverinfo="text",
        name="nodes",
    )

    fig = go.Figure(data=[edge_trace, edge_label_trace, node_trace])
    scope_title = {
        "all": "All",
        "tech": "Tech Actor Reachable",
        "market": "Market Actor Reachable",
    }.get(actor_scope, "All")
    fig.update_layout(
        title=f"Strategy Ontology Graph · {scope_title}",
        showlegend=False,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig
