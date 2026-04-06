"""View model builders for case replay UI."""

from __future__ import annotations

import math
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
        if previous_max_overlap <= 0.0 < max_overlap:
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
        return int(str(node_id).rsplit("-", maxsplit=1)[-1])
    except ValueError:
        return 0


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _clip(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _average_overlap(snapshot: dict[str, Any]) -> float:
    values = [_safe_float(v) for v in (snapshot.get("user_overlap") or {}).values()]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _build_hypothesis_steps(result: dict[str, Any]) -> list[dict[str, Any]]:
    timeline = result.get("timeline", [])
    ontology_setup = result.get("ontology_setup") or {}
    space_summary = ontology_setup.get("space_summary") or {}

    adoption_resistance = _safe_float(space_summary.get("adoption_resistance"), 0.6)
    incumbent_response_speed = _safe_float(space_summary.get("incumbent_response_speed"), 0.5)
    value_perception_gap = _safe_float(space_summary.get("value_perception_gap"), 0.5)

    steps: list[dict[str, Any]] = []
    for index, snapshot in enumerate(timeline, start=1):
        step_value = snapshot.get("step") or index
        competition_edge_count = len(snapshot.get("competition_edges") or [])
        average_overlap = _average_overlap(snapshot)
        max_overlap = max([_safe_float(v) for v in (snapshot.get("user_overlap") or {}).values()] or [0.0])

        steps.append(
            {
                "step_id": f"step-{step_value}",
                "step": int(step_value),
                "hypothesis_label": f"Hypothesis step {step_value}",
                "state_vector": {
                    "average_overlap": round(average_overlap, 4),
                    "max_overlap": round(max_overlap, 4),
                    "competition_edge_count": competition_edge_count,
                    "adoption_resistance": round(adoption_resistance, 4),
                    "incumbent_response_speed": round(incumbent_response_speed, 4),
                    "value_perception_gap": round(value_perception_gap, 4),
                },
                "hypotheses": [
                    {
                        "hypothesis_id": f"H{step_value}-overlap",
                        "description": "User overlap remains sufficient to sustain competitive transfer.",
                        "variable": "average_overlap",
                        "expected": 0.45,
                        "observed": round(average_overlap, 4),
                    },
                    {
                        "hypothesis_id": f"H{step_value}-resistance",
                        "description": "Adoption resistance stays below hard-friction regime.",
                        "variable": "adoption_resistance",
                        "expected": 0.6,
                        "observed": round(adoption_resistance, 4),
                    },
                ],
            }
        )

    return steps


def _build_feature_deltas_from_gaps(
    causal_gap_links: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    per_node_delta: dict[str, dict[str, Any]] = {}
    factor_to_delta: dict[str, dict[str, float]] = {
        "simulated_vs_real_outcome": {"average_overlap": -0.12, "adoption_resistance": 0.15},
        "adoption_resistance": {"adoption_resistance": 0.20},
        "pilot_success_to_scale": {"value_perception_gap": 0.18, "incumbent_response_speed": 0.10},
    }

    for link in causal_gap_links:
        node_id = str(link.get("target_node_id") or "").strip()
        factor = str(link.get("summary") or "").strip()
        if not node_id or not factor:
            continue
        deltas = factor_to_delta.get(factor, {})
        if not deltas:
            continue
        bucket = per_node_delta.setdefault(node_id, {"factor_deltas": {}, "factors": []})
        for key, value in deltas.items():
            current = _safe_float(bucket["factor_deltas"].get(key), 0.0)
            bucket["factor_deltas"][key] = round(current + value, 6)
        if factor not in bucket["factors"]:
            bucket["factors"].append(factor)

    return per_node_delta


def _compute_transition_weight(
    features: dict[str, float],
    coefficients: dict[str, float],
) -> tuple[float, float, dict[str, float]]:
    score = coefficients.get("intercept", 0.0)
    contributions: dict[str, float] = {}
    for name, value in features.items():
        beta = coefficients.get(name, 0.0)
        contribution = beta * value
        contributions[name] = round(contribution, 6)
        score += contribution
    return _sigmoid(score), score, contributions


def _build_weighted_transitions(
    *,
    result: dict[str, Any],
    graph_edges: list[dict[str, Any]],
    hypothesis_steps: list[dict[str, Any]],
    causal_gap_links: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    step_state = {str(step.get("step_id")): step.get("state_vector", {}) for step in hypothesis_steps}
    gap_feature_deltas = _build_feature_deltas_from_gaps(causal_gap_links)

    ontology_setup = result.get("ontology_setup") or {}
    coefficients = {
        "intercept": -0.35,
        "average_overlap": 2.10,
        "adoption_resistance": -1.85,
        "incumbent_response_speed": -1.10,
        "value_perception_gap": -1.25,
        "competition_pressure": 0.75,
    }
    calibrated = (ontology_setup.get("weight_model") or {}).get("calibrated_beta") if isinstance(ontology_setup, dict) else None
    calibrated_coefficients = dict(coefficients)
    if isinstance(calibrated, dict):
        for key, value in calibrated.items():
            if key in calibrated_coefficients:
                calibrated_coefficients[key] = _safe_float(value, calibrated_coefficients[key])

    weighted_transitions: list[dict[str, Any]] = []
    edge_overrides: list[dict[str, Any]] = []

    for edge in graph_edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in step_state:
            continue

        source_state = step_state[source]
        baseline_features = {
            "average_overlap": _clip(_safe_float(source_state.get("average_overlap"), 0.0)),
            "adoption_resistance": _clip(_safe_float(source_state.get("adoption_resistance"), 0.6)),
            "incumbent_response_speed": _clip(_safe_float(source_state.get("incumbent_response_speed"), 0.5)),
            "value_perception_gap": _clip(_safe_float(source_state.get("value_perception_gap"), 0.5)),
            "competition_pressure": _clip(_safe_float(source_state.get("competition_edge_count"), 0.0) / 5.0),
        }

        adjusted_features = dict(baseline_features)
        node_delta = gap_feature_deltas.get(source, {})
        for key, delta in (node_delta.get("factor_deltas") or {}).items():
            adjusted_features[key] = _clip(_safe_float(adjusted_features.get(key), 0.0) + _safe_float(delta, 0.0))

        baseline_weight, baseline_score, baseline_contrib = _compute_transition_weight(
            baseline_features,
            coefficients=calibrated_coefficients,
        )
        adjusted_weight, adjusted_score, adjusted_contrib = _compute_transition_weight(
            adjusted_features,
            coefficients=calibrated_coefficients,
        )

        hard_constraint = None
        if adjusted_features["adoption_resistance"] >= 0.9:
            hard_constraint = {
                "constraint_id": "HC-high-adoption-resistance",
                "description": "Adoption resistance above 0.90 forces transition freeze.",
                "applied": True,
                "forced_weight": 0.0,
            }
            adjusted_weight = 0.0
        elif (
            adjusted_features["average_overlap"] >= 0.95
            and adjusted_features["adoption_resistance"] <= 0.2
        ):
            hard_constraint = {
                "constraint_id": "HC-lockin-overlap",
                "description": "Very high overlap with low resistance forces transition lock-in.",
                "applied": True,
                "forced_weight": 1.0,
            }
            adjusted_weight = 1.0

        sensitivity_entries: list[dict[str, Any]] = []
        logistic_slope = adjusted_weight * (1.0 - adjusted_weight)
        for feature_name, feature_value in adjusted_features.items():
            beta = calibrated_coefficients.get(feature_name, 0.0)
            partial_derivative = logistic_slope * beta
            sensitivity_entries.append(
                {
                    "feature": feature_name,
                    "feature_value": round(feature_value, 6),
                    "partial_derivative": round(partial_derivative, 6),
                    "absolute_sensitivity": round(abs(partial_derivative), 6),
                }
            )
        sensitivity_entries.sort(key=lambda item: item["absolute_sensitivity"], reverse=True)

        transition_id = f"transition:{source}->{target}"
        weighted_transitions.append(
            {
                "transition_id": transition_id,
                "source": source,
                "target": target,
                "driver_formula": "sigmoid(b0 + b_overlap*x_overlap + b_resistance*x_resistance + b_incumbent*x_incumbent + b_value_gap*x_value_gap + b_competition*x_competition)",
                "prior_beta": coefficients,
                "calibrated_beta": calibrated_coefficients,
                "baseline_weight": round(baseline_weight, 6),
                "adjusted_weight": round(adjusted_weight, 6),
                "baseline_score": round(baseline_score, 6),
                "adjusted_score": round(adjusted_score, 6),
                "driver_terms": {
                    "baseline": baseline_contrib,
                    "adjusted": adjusted_contrib,
                },
                "hard_constraint": hard_constraint,
                "sensitivity_analysis": sensitivity_entries,
            }
        )

        if abs(adjusted_weight - baseline_weight) >= 1e-6 or hard_constraint is not None:
            edge_overrides.append(
                {
                    "override_id": f"override:{source}->{target}",
                    "edge_id": edge.get("id", f"{source}->{target}"),
                    "source": source,
                    "target": target,
                    "factors": list(node_delta.get("factors") or []),
                    "baseline_weight": round(baseline_weight, 6),
                    "adjusted_weight": round(adjusted_weight, 6),
                    "delta": round(adjusted_weight - baseline_weight, 6),
                    "hard_constraint": hard_constraint,
                }
            )

    return weighted_transitions, edge_overrides


def _build_gap_overlays(causal_gap_links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    overlays: list[dict[str, Any]] = []
    for index, link in enumerate(causal_gap_links, start=1):
        source_node_id = str(link.get("target_node_id") or "").strip()
        if not source_node_id:
            continue
        label = str(link.get("summary") or link.get("gap_id") or f"gap-{index}").strip()
        overlays.append(
            {
                "overlay_id": str(link.get("gap_id") or f"gap-overlay-{index}"),
                "overlay_type": "gap",
                "source_node_id": source_node_id,
                "label": label,
                "trace_type": str(link.get("trace_type") or "branch_point"),
            }
        )
    return overlays


def _build_control_overlays(editable_controls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    overlays: list[dict[str, Any]] = []
    for index, control in enumerate(editable_controls, start=1):
        source_node_id = str(control.get("source_node_id") or "").strip()
        if not source_node_id:
            continue
        label = str(control.get("label") or control.get("control_id") or f"control-{index}").strip()
        current_value = control.get("current_value")
        if current_value is not None:
            label = f"{label}: {current_value}"
        overlays.append(
            {
                "overlay_id": str(control.get("control_id") or f"control-overlay-{index}"),
                "overlay_type": "control",
                "source_node_id": source_node_id,
                "label": label,
                "control_type": str(control.get("control_type") or "parameter"),
            }
        )
    return overlays


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
    gap_overlays = _build_gap_overlays(causal_gap_links)
    control_overlays = _build_control_overlays(editable_controls)
    hypothesis_steps = _build_hypothesis_steps(result)
    weighted_transitions, edge_overrides = _build_weighted_transitions(
        result=result,
        graph_edges=edges,
        hypothesis_steps=hypothesis_steps,
        causal_gap_links=causal_gap_links,
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
        "hypothesis_steps": hypothesis_steps,
        "weighted_transitions": weighted_transitions,
        "edge_overrides": edge_overrides,
        "gap_overlays": gap_overlays,
        "control_overlays": control_overlays,
        "causal_trace_options": causal_options,
        "causal_gap_links": causal_gap_links,
        "editable_controls": editable_controls,
        "evidence_panel": evidence_panel,
    }
