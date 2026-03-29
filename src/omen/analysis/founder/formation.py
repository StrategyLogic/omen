"""Strategic formation chain builder (local, explainable skeleton)."""

from __future__ import annotations

import re
from typing import Any


def _index_by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        if item_id:
            index[item_id] = item
    return index


def _relation_name(influence: dict[str, Any]) -> str:
    return str(influence.get("type") or influence.get("relationship") or "influences").strip() or "influences"


def _founder_actor(founder_ontology: dict[str, Any]) -> dict[str, Any] | None:
    actors = founder_ontology.get("actors") or []
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        if str(actor.get("type") or "").strip().lower() == "founder":
            return actor
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        actor_id = str(actor.get("id") or "").lower()
        actor_name = str(actor.get("name") or "").lower()
        if "founder" in actor_id or "founder" in actor_name:
            return actor
    return None


def _event_by_id(founder_ontology: dict[str, Any], event_id: str) -> dict[str, Any] | None:
    events = [event for event in (founder_ontology.get("events") or []) if isinstance(event, dict)]

    normalized_target = str(event_id or "").strip()
    if not normalized_target:
        return None

    # Primary path: exact ID match.
    for event in events:
        if not isinstance(event, dict):
            continue
        if str(event.get("id") or "").strip() == normalized_target:
            return event

    # Compatibility path: accept legacy/event-index aliases like event-2, event.2, event_2.
    alias = normalized_target.lower()
    match = re.fullmatch(r"event[-_.]?(\d+)", alias)
    if match:
        index = int(match.group(1)) - 1
        if 0 <= index < len(events):
            return events[index]

    # Secondary path: allow matching by event name token.
    for event in events:
        event_name = str(event.get("name") or "").strip().lower()
        if event_name and event_name == alias:
            return event

    return None


def build_strategic_formation_chain(
    *,
    founder_ontology: dict[str, Any],
    target_event_id: str,
) -> dict[str, Any]:
    target_event = _event_by_id(founder_ontology, target_event_id)
    if target_event is None:
        raise ValueError(f"target event not found: {target_event_id}")

    actors = founder_ontology.get("actors") or []
    products = founder_ontology.get("products") or []
    events = founder_ontology.get("events") or []
    influences = founder_ontology.get("influences") or []

    actor_index = _index_by_id([item for item in actors if isinstance(item, dict)])
    product_index = _index_by_id([item for item in products if isinstance(item, dict)])
    event_index = _index_by_id([item for item in events if isinstance(item, dict)])

    founder_actor = _founder_actor(founder_ontology)
    founder_name = str((founder_actor or {}).get("name") or "Founder").strip() or "Founder"
    founder_profile = (founder_actor or {}).get("profile") or {}
    mental_patterns = (founder_profile.get("mental_patterns") if isinstance(founder_profile, dict) else {}) or {}
    strategic_style = (founder_profile.get("strategic_style") if isinstance(founder_profile, dict) else {}) or {}

    perception_signals: list[dict[str, Any]] = []
    external_pressures: list[dict[str, Any]] = []
    execution_delta: list[dict[str, Any]] = []
    evidence_refs: list[str] = []

    target_event_refs = target_event.get("evidence_refs") or []
    evidence_refs.extend(str(ref) for ref in target_event_refs if str(ref).strip())

    for influence in influences:
        if not isinstance(influence, dict):
            continue
        relation = _relation_name(influence)
        source = str(influence.get("source") or "").strip()
        target = str(influence.get("target") or "").strip()
        description = str(influence.get("description") or "").strip()
        refs = influence.get("evidence_refs") or []

        if target == target_event_id:
            source_name = (
                str((actor_index.get(source) or product_index.get(source) or event_index.get(source) or {}).get("name") or source)
                .strip()
                or source
            )
            item = {
                "source": source,
                "source_name": source_name,
                "relation": relation,
                "description": description,
            }
            perception_signals.append(item)

            source_actor = actor_index.get(source)
            source_type = str((source_actor or {}).get("type") or "").lower()
            if source_type in {"competitor", "investor", "regulator", "organization", "customer"}:
                external_pressures.append(item)

            evidence_refs.extend(str(ref) for ref in refs if str(ref).strip())

        if source == target_event_id:
            target_name = (
                str((actor_index.get(target) or product_index.get(target) or event_index.get(target) or {}).get("name") or target)
                .strip()
                or target
            )
            execution_delta.append(
                {
                    "target": target,
                    "target_name": target_name,
                    "relation": relation,
                    "description": description,
                }
            )
            evidence_refs.extend(str(ref) for ref in refs if str(ref).strip())

    internal_constraints = list(target_event.get("context_constraints") or [])

    mediators = {
        "core_beliefs": list(mental_patterns.get("core_beliefs") or []),
        "cognitive_frames": list(mental_patterns.get("cognitive_frames") or []),
        "decision_style": str(strategic_style.get("decision_style") or "").strip(),
        "non_negotiables": list(strategic_style.get("non_negotiables") or []),
    }

    dedup_evidence_refs = list(dict.fromkeys(ref for ref in evidence_refs if ref))

    formation_chain = {
        "perception": perception_signals,
        "constraint_conflict": {
            "internal_constraints": internal_constraints,
            "external_pressures": external_pressures,
        },
        "mediation": mediators,
        "decision_logic": {
            "event_id": target_event_id,
            "event_name": str(target_event.get("name") or target_event_id),
            "description": str(target_event.get("description") or "").strip(),
        },
        "execution_delta": execution_delta,
    }

    return {
        "query": {
            "type": "formation",
            "target_event_id": target_event_id,
        },
        "formation_chain": formation_chain,
        "counterfactual_analysis": {
            "status": "pending",
            "note": "Counterfactual analysis is pending in current iteration.",
        },
        "evidence_refs": dedup_evidence_refs,
        "summary": {
            "founder": founder_name,
            "perception_signal_count": len(perception_signals),
            "internal_constraint_count": len(internal_constraints),
            "external_pressure_count": len(external_pressures),
            "execution_delta_count": len(execution_delta),
        },
    }
