"""Graph-constrained scenario planning input preparation."""

from __future__ import annotations

from typing import Any

import networkx as nx

from omen.scenario.models import ScenarioPlanningRuleTemplateModel, StrategyActorPlanningQueryResultModel


def _normalize_signal_query_payload(signal: dict[str, Any]) -> dict[str, Any]:
    name = str(signal.get("name") or "").strip()
    payload: dict[str, Any] = {
        "name": name,
        "kind": "signal",
    }

    signal_id = str(signal.get("signal_id") or name).strip()
    if signal_id:
        payload["signal_id"] = signal_id

    for field_name in ("domain", "direction", "mechanism_note", "impact_summary"):
        value = str(signal.get(field_name) or "").strip()
        if value:
            payload[field_name] = value

    strength = signal.get("strength")
    if strength is not None:
        payload["strength"] = float(strength)

    mapped_targets = [item for item in list(signal.get("mapped_targets") or []) if isinstance(item, dict)]
    if mapped_targets:
        payload["mapped_targets"] = mapped_targets

    cascade_rules = [item for item in list(signal.get("cascade_rules") or []) if isinstance(item, dict)]
    if cascade_rules:
        payload["cascade_rules"] = cascade_rules

    market_constraints = [item for item in list(signal.get("market_constraints") or []) if isinstance(item, dict)]
    if market_constraints:
        payload["market_constraints"] = market_constraints

    return payload


def build_planning_query(
    *,
    situation_artifact: dict[str, Any],
    actor_ref: str,
    template: ScenarioPlanningRuleTemplateModel,
) -> dict[str, Any]:
    situation_id = str(situation_artifact.get("id") or "unknown")
    graph = nx.DiGraph()
    graph.add_node(f"situation::{situation_id}", kind="situation")
    graph.add_node(f"actor::{actor_ref}", kind="actor")
    graph.add_edge(f"actor::{actor_ref}", f"situation::{situation_id}", relation="influences")

    space_inputs: list[dict[str, Any]] = []
    for signal in list(situation_artifact.get("signals") or []):
        if not isinstance(signal, dict):
            continue
        name = str(signal.get("name") or "").strip()
        if not name:
            continue
        signal_node = f"signal::{name}"
        graph.add_node(signal_node, kind="signal")
        graph.add_edge(signal_node, f"situation::{situation_id}", relation="describes")
        space_inputs.append(_normalize_signal_query_payload(signal))

    if not space_inputs:
        space_inputs.append({"name": "fallback_signal", "kind": "signal"})

    constraints = list((situation_artifact.get("context") or {}).get("hard_constraints") or [])
    constraint_signals = [{"name": str(item), "kind": "constraint"} for item in constraints if str(item).strip()]

    # Keep local preparation deterministic and structural; semantic planning stays in LLM.
    similarity_scores = [
        {
            "scenario_key": slot.scenario_key,
            "score": float(slot.default_prior),
            "source": "planning_template_default",
        }
        for slot in sorted(template.slot_policy, key=lambda item: item.scenario_key)
    ]

    query = StrategyActorPlanningQueryResultModel(
        situation_id=situation_id,
        actor_ref=actor_ref,
        space_inputs=space_inputs,
        constraint_signals=constraint_signals,
        similarity_scores=similarity_scores,
        query_version="planning_query_v1",
    )
    payload = query.model_dump()
    payload["graph_stats"] = {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
    }
    return payload
