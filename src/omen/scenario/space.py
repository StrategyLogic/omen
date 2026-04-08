"""Graph-constrained scenario planning input preparation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from omen.scenario.models import ScenarioPlanningRuleTemplateModel, StrategyActorPlanningQueryResultModel


def _normalize_similarity_scores(scores: dict[str, float], *, source: str) -> list[dict[str, Any]]:
    total = sum(max(0.0, float(value)) for value in scores.values())
    if total <= 0.0:
        total = 1.0
    return [
        {
            "scenario_key": key,
            "score": round(max(0.0, float(value)) / total, 6),
            "source": source,
        }
        for key, value in sorted(scores.items())
    ]


def _extract_strategic_style(actor_ref: str) -> dict[str, Any] | None:
    candidate = Path(str(actor_ref).strip())
    if not candidate.exists() or candidate.suffix.lower() != ".json":
        return None

    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception:
        return None

    actors = payload.get("actors") or []
    if not isinstance(actors, list):
        return None

    for actor in actors:
        if not isinstance(actor, dict):
            continue
        if str(actor.get("type") or "").strip() != "StrategicActor":
            continue
        profile = actor.get("profile") or {}
        style = profile.get("strategic_style") or {}
        return style if isinstance(style, dict) else None
    return None


def _is_style_usable(style: dict[str, Any] | None) -> bool:
    if not isinstance(style, dict):
        return False
    filled = 0
    if str(style.get("decision_style") or "").strip():
        filled += 1
    if str(style.get("value_proposition") or "").strip():
        filled += 1
    if isinstance(style.get("decision_preferences"), list) and any(str(x).strip() for x in style["decision_preferences"]):
        filled += 1
    if isinstance(style.get("non_negotiables"), list) and any(str(x).strip() for x in style["non_negotiables"]):
        filled += 1
    return filled >= 2


def _build_actor_weighted_similarity_scores(
    *,
    template: ScenarioPlanningRuleTemplateModel,
    actor_ref: str,
) -> list[dict[str, Any]]:
    default_scores = {
        slot.scenario_key: float(slot.default_prior)
        for slot in sorted(template.slot_policy, key=lambda item: item.scenario_key)
    }

    style = _extract_strategic_style(actor_ref)
    if not _is_style_usable(style):
        return _normalize_similarity_scores(default_scores, source="planning_template_default")

    assert isinstance(style, dict)
    style_text_parts: list[str] = []
    for field in ("decision_style", "value_proposition"):
        value = str(style.get(field) or "").strip()
        if value:
            style_text_parts.append(value)

    for field in ("decision_preferences", "non_negotiables"):
        value = style.get(field)
        if isinstance(value, list):
            style_text_parts.extend(str(item).strip() for item in value if str(item).strip())

    corpus = " ".join(style_text_parts).lower()

    # Reset mode: derive A/B/C directly from actor-style similarity, then normalize.
    # No additive adjustment on top of planning template defaults.
    token_groups: dict[str, set[str]] = {
        "A": {
            "aggressive",
            "offense",
            "offensive",
            "proactive",
            "growth",
            "expand",
            "expansion",
            "bold",
            "invest",
            "investment",
            "acquisition",
            "integrat",
            "partnership",
            "ecosystem",
            "capture",
            "breakthrough",
        },
        "B": {
            "conservative",
            "defense",
            "defensive",
            "risk",
            "compliance",
            "stability",
            "protect",
            "cost control",
            "efficiency",
            "discipline",
            "survival",
            "continuity",
            "resilience",
            "guardrail",
        },
        "C": {
            "confront",
            "confrontation",
            "compete",
            "competition",
            "rival",
            "attack",
            "disrupt",
            "counter",
            "zero-sum",
            "war",
            "escalation",
        },
    }

    similarity_scores: dict[str, float] = {"A": 0.0, "B": 0.0, "C": 0.0}
    for key, tokens in token_groups.items():
        score = 0.0
        for token in tokens:
            if token in corpus:
                score += 1.0
        similarity_scores[key] = score

    if sum(similarity_scores.values()) <= 0.0:
        return _normalize_similarity_scores(default_scores, source="planning_template_default")

    return _normalize_similarity_scores(similarity_scores, source="actor_style_similarity_reset")


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
    similarity_scores = _build_actor_weighted_similarity_scores(
        template=template,
        actor_ref=actor_ref,
    )

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
