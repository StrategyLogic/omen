"""View model builders for Spec 6 case replay UI."""

from __future__ import annotations

from typing import Any

from omen.ui.causal_trace import build_causal_gap_links
from omen.ui.editable_controls import build_editable_controls


def _build_market_signal(adoption_resistance: Any) -> str | None:
    if isinstance(adoption_resistance, (int, float)):
        value = float(adoption_resistance)
        if value >= 0.75:
            return f"Adoption resistance high ({value:.2f})"
        if value >= 0.5:
            return f"Adoption resistance active ({value:.2f})"
        if value > 0:
            return f"Adoption resistance low ({value:.2f})"
        return None
    if adoption_resistance is None:
        return None
    text = str(adoption_resistance).strip()
    return f"Adoption resistance: {text}" if text else None


def _build_graph_nodes(result: dict[str, Any]) -> list[dict[str, Any]]:
    timeline = result.get("timeline", [])
    ontology_setup = result.get("ontology_setup") or {}
    space_summary = ontology_setup.get("space_summary") or {}
    market_signal = _build_market_signal(space_summary.get("adoption_resistance"))
    nodes: list[dict[str, Any]] = []
    previous_max_overlap = 0.0
    previous_competition_edges = 0
    previous_leader_actor_id: str | None = None

    for index, snapshot in enumerate(timeline, start=1):
        step = snapshot.get("step") or index
        overlap_values = [float(v) for v in (snapshot.get("user_overlap") or {}).values()]
        max_overlap = max(overlap_values) if overlap_values else 0.0
        competition_edges = snapshot.get("competition_edges") or []
        competition_edge_count = len(competition_edges)

        actor_states = snapshot.get("actors") or {}
        leader_actor_id = "unknown"
        leader_user_edges = 0
        if isinstance(actor_states, dict) and actor_states:
            leader_actor_id, leader_payload = max(
                actor_states.items(),
                key=lambda item: int((item[1] or {}).get("user_edge_count") or 0),
            )
            leader_user_edges = int((leader_payload or {}).get("user_edge_count") or 0)

        event = "Stable progression"
        if previous_max_overlap <= 0.0 and max_overlap > 0.0:
            event = "User overlap emerges"
        elif competition_edge_count > 0 and previous_competition_edges == 0:
            event = "Competition activated"
        elif previous_leader_actor_id and leader_actor_id != previous_leader_actor_id:
            event = "Leader shift"
        elif competition_edge_count > previous_competition_edges:
            event = "Competition expands"
        elif max_overlap > previous_max_overlap:
            event = "Overlap intensifies"

        label_event = event
        if market_signal:
            label_event = market_signal if event == "Stable progression" else f"{event} | {market_signal}"

        summary = (
            f"{label_event} · leader={leader_actor_id}({leader_user_edges}) · "
            f"max_overlap={max_overlap:.2f} · competition_edges={competition_edge_count}"
        )
        nodes.append(
            {
                "id": f"step-{step}",
                "label": f"Step {step}: {label_event}",
                "kind": "phase",
                "evidence_level": "medium",
                "event": event,
                "market_signal": market_signal,
                "summary": summary,
                "leader_actor_id": leader_actor_id,
                "max_overlap": round(max_overlap, 4),
                "competition_edge_count": competition_edge_count,
            }
        )

        previous_max_overlap = max_overlap
        previous_competition_edges = competition_edge_count
        previous_leader_actor_id = leader_actor_id

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


def _step_index(node_id: str) -> int:
    try:
        return int(str(node_id).split("-")[-1])
    except ValueError:
        return 0


def _resolve_real_world_outcome(
    result: dict[str, Any],
    explanation: dict[str, Any],
) -> str | None:
    for candidate in (
        result.get("real_world_outcome"),
        result.get("known_outcome"),
        explanation.get("known_outcome"),
    ):
        if candidate is None:
            continue
        text = str(candidate).strip()
        if text:
            return text
    return None


def _build_reality_graph(
    *,
    nodes: list[dict[str, Any]],
    causal_gap_links: list[dict[str, Any]],
    reality_gaps: list[dict[str, Any]],
    result: dict[str, Any],
    explanation: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    node_ids = [str(node.get("id") or "") for node in nodes if node.get("id")]
    node_id_set = set(node_ids)

    overlap_targets = sorted(
        {
            str(link.get("target_node_id") or "")
            for link in causal_gap_links
            if str(link.get("target_node_id") or "") in node_id_set
        },
        key=_step_index,
    )

    first_model_node_id = node_ids[0] if node_ids else None
    overlap_anchor = overlap_targets[0] if overlap_targets else first_model_node_id

    reality_nodes: list[dict[str, Any]] = []
    reality_path_node_ids: list[str] = []
    if overlap_anchor:
        reality_path_node_ids.append(overlap_anchor)

    for index, gap in enumerate(reality_gaps, start=1):
        factor = str(gap.get("factor") or "reality_gap").strip() or "reality_gap"
        observation = str(gap.get("reality_observation") or "").strip()
        significance = str(gap.get("gap_significance") or "medium").strip() or "medium"
        node_id = f"real-gap-{index}"
        label = f"Reality {index}: {factor}"
        summary = observation or str(gap.get("suggested_calibration") or factor)
        reality_nodes.append(
            {
                "id": node_id,
                "label": label,
                "kind": "reality_gap",
                "evidence_level": significance,
                "event": "Reality divergence",
                "summary": summary,
                "factor": factor,
            }
        )
        reality_path_node_ids.append(node_id)

    real_outcome = _resolve_real_world_outcome(result, explanation)
    if real_outcome:
        real_end_id = "real-end"
        reality_nodes.append(
            {
                "id": real_end_id,
                "label": "Reality End",
                "kind": "reality_outcome",
                "evidence_level": "high",
                "event": "Real-world outcome",
                "summary": real_outcome,
                "outcome": real_outcome,
            }
        )
        reality_path_node_ids.append(real_end_id)

    if len(reality_path_node_ids) < 2 and overlap_targets:
        reality_path_node_ids = overlap_targets

    reality_edges: list[dict[str, Any]] = []
    for source, target in zip(reality_path_node_ids, reality_path_node_ids[1:], strict=False):
        if source == target:
            continue
        reality_edges.append(
            {
                "id": f"reality:{source}->{target}",
                "source": source,
                "target": target,
            }
        )

    return reality_nodes, reality_edges


def build_case_replay_view_model(
    *,
    result: dict[str, Any],
    explanation: dict[str, Any],
    case_id: str,
) -> dict[str, Any]:
    nodes = _build_graph_nodes(result)
    edges = _build_graph_edges(result)
    ontology_setup = result.get("ontology_setup") or {}
    space_summary = ontology_setup.get("space_summary") or {}

    branch_points = explanation.get("branch_points", [])
    reality_gaps = explanation.get("reality_gap_analysis", [])
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

    editable_controls = build_editable_controls(result)
    causal_gap_links = build_causal_gap_links(branch_points, reality_gaps, nodes)
    reality_graph_nodes, reality_graph_edges = _build_reality_graph(
        nodes=nodes,
        causal_gap_links=causal_gap_links,
        reality_gaps=reality_gaps,
        result=result,
        explanation=explanation,
    )

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
        "space_summary": space_summary,
        "graph_nodes": nodes,
        "graph_edges": edges,
        "reality_graph_nodes": reality_graph_nodes,
        "reality_graph_edges": reality_graph_edges,
        "causal_trace_options": causal_options,
        "causal_gap_links": causal_gap_links,
        "editable_controls": editable_controls,
        "evidence_panel": evidence_panel,
    }
