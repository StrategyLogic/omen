"""Assemble top-level strategy ontology with extracted slices."""

from __future__ import annotations

from typing import Any

from omen.ingest.synthesizer.builders.actor import actor_hash


def _build_identity_map(founder_ontology: dict[str, Any]) -> dict[str, str]:
    actors = founder_ontology.get("actors")
    if not isinstance(actors, list):
        return {}

    mapping: dict[str, str] = {}
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        shared_id = str(actor.get("shared_id") or "").strip()
        founder_id = str(actor.get("id") or "").strip()
        if shared_id and founder_id:
            mapping[shared_id] = founder_id
    return mapping


def attach_timeline_events(
    strategy_ontology: dict[str, Any],
    timeline_events: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = dict(strategy_ontology)
    abox_value = payload.get("abox")
    abox: dict[str, Any] = abox_value if isinstance(abox_value, dict) else {}
    normalized_events: list[dict[str, Any]] = []
    for event in timeline_events:
        if not isinstance(event, dict):
            continue
        normalized_events.append(
            {
                "event_id": str(event.get("id") or ""),
                "time": str(event.get("time") or "unknown"),
                "event": str(event.get("event") or "other"),
                "description": str(event.get("description") or event.get("event") or ""),
                "evidence_refs": event.get("evidence_refs") if isinstance(event.get("evidence_refs"), list) else [],
                "confidence": float(event.get("confidence") or 0.5),
                "is_strategy_related": bool(event.get("is_strategy_related", True)),
            }
        )
    abox["events"] = normalized_events
    payload["abox"] = abox
    return payload


def attach_founder_ref(
    strategy_ontology: dict[str, Any],
    founder_ontology: dict[str, Any],
    *,
    founder_filename: str,
) -> dict[str, Any]:
    payload = dict(strategy_ontology)
    founder_meta_value = founder_ontology.get("meta")
    founder_meta: dict[str, Any] = founder_meta_value if isinstance(founder_meta_value, dict) else {}
    payload["founder_ref"] = {
        "path": founder_filename,
        "version": str(founder_meta.get("version") or "1.0.0"),
        "hash": actor_hash(founder_ontology),
        "identity_map": _build_identity_map(founder_ontology),
    }
    return payload


def attach_actor_ref(
    strategy_ontology: dict[str, Any],
    actor_ontology: dict[str, Any],
    *,
    actor_filename: str,
) -> dict[str, Any]:
    payload = dict(strategy_ontology)
    actor_meta_value = actor_ontology.get("meta")
    actor_meta: dict[str, Any] = actor_meta_value if isinstance(actor_meta_value, dict) else {}
    payload["actor_ref"] = {
        "path": actor_filename,
        "version": str(actor_meta.get("version") or "1.0.0"),
        "hash": actor_hash(actor_ontology),
        "identity_map": _build_identity_map(actor_ontology),
    }
    return payload
