"""Founder query skeleton (local, no LLM)."""

from __future__ import annotations

from typing import Any


def snapshot_by_year(founder_ontology: dict[str, Any], year: int) -> dict[str, Any]:
    events = founder_ontology.get("events") or []
    year_text = str(year)
    filtered = [event for event in events if year_text in str(event.get("date") or event.get("time") or "")]
    return {
        "year": year,
        "events": filtered,
    }


def _as_time_text(value: Any) -> str:
    return str(value or "").strip()


def _classify_event_type(text: str) -> str:
    value = text.lower()
    if any(token in value for token in ("launch", "launched", "上线", "发布")):
        return "launch"
    if any(token in value for token in ("release", "版本", "edition")):
        return "release"
    if any(token in value for token in ("pilot", "试点", "试用", "验证")):
        return "pilot"
    if any(token in value for token in ("pricing", "定价", "commercial", "付费")):
        return "pricing"
    if any(token in value for token in ("expand", "expansion", "market", "市场")):
        return "expansion"
    return "other"


def _normalize_event_type(value: Any, description: str) -> str:
    candidate = str(value or "").strip().lower()
    if not candidate:
        return _classify_event_type(description)
    if " " in candidate or len(candidate) > 24:
        return _classify_event_type(description or candidate)
    return candidate


def _time_matches(value: str, year: int | None, date: str | None) -> bool:
    if not value:
        return year is None and not date
    if year is not None and str(year) not in value:
        return False
    if date and date not in value:
        return False
    return True


def _filter_strategy_events(
    strategy_ontology: dict[str, Any],
    *,
    year: int | None,
    date: str | None,
) -> list[dict[str, Any]]:
    abox = strategy_ontology.get("abox") or {}
    raw_events = abox.get("events") or []
    items: list[dict[str, Any]] = []
    for event in raw_events:
        if not isinstance(event, dict):
            continue
        time_text = _as_time_text(event.get("time") or event.get("date"))
        if not _time_matches(time_text, year, date):
            continue
        items.append(
            {
                "event_id": str(event.get("event_id") or event.get("id") or "").strip() or "unknown",
                "time": time_text or "unknown",
                "event": str(event.get("event") or event.get("type") or "").strip() or "unknown",
                "description": str(event.get("description") or event.get("content") or "").strip(),
                "evidence_refs": event.get("evidence_refs") or [],
                "confidence": event.get("confidence") if event.get("confidence") is not None else "medium",
                "is_strategy_related": bool(event.get("is_strategy_related", True)),
            }
        )
    return items


def _timeline_from_founder_events(founder_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for event in founder_events:
        raw_text = str(event.get("event") or event.get("description") or "").strip()
        event_type = _normalize_event_type(
            event.get("type") or event.get("label") or event.get("event"),
            raw_text,
        )
        timeline.append(
            {
                "event_id": str(event.get("id") or "").strip() or "unknown",
                "time": _as_time_text(event.get("date") or event.get("time")) or "unknown",
                "event": event_type,
                "description": str(event.get("description") or raw_text).strip(),
                "evidence_refs": event.get("evidence_refs") or [],
                "confidence": event.get("confidence") if event.get("confidence") is not None else "medium",
                "is_strategy_related": bool(event.get("is_strategy_related", True)),
            }
        )
    return timeline


def _filter_founder_events(
    founder_ontology: dict[str, Any],
    *,
    year: int | None,
    date: str | None,
) -> list[dict[str, Any]]:
    raw_events = founder_ontology.get("events") or []
    filtered: list[dict[str, Any]] = []
    for event in raw_events:
        if not isinstance(event, dict):
            continue
        time_text = _as_time_text(event.get("date") or event.get("time"))
        if not _time_matches(time_text, year, date):
            continue
        filtered.append(event)
    return filtered


def _normalize_ref_id(value: Any) -> str:
    token = str(value or "").strip()
    return token


def _resolve_node_id(raw_id: Any, known_ids: set[str]) -> str:
    token = _normalize_ref_id(raw_id)
    if not token:
        return ""
    prefixes = ("event_", "event.", "event-")
    candidates = [token]
    for prefix in prefixes:
        if token.startswith(prefix):
            candidates.append(token[len(prefix) :])
    for candidate in candidates:
        if candidate in known_ids:
            return candidate
    for prefix in prefixes:
        candidate = f"{prefix}{token}"
        if candidate in known_ids:
            return candidate
    return ""


def _resolve_influence_endpoint(
    influence: dict[str, Any],
    *,
    primary_key: str,
    legacy_event_key: str,
    legacy_constraint_key: str,
    known_ids: set[str],
) -> str:
    direct = _resolve_node_id(influence.get(primary_key), known_ids)
    if direct:
        return direct

    legacy_event = _resolve_node_id(influence.get(legacy_event_key), known_ids)
    if legacy_event:
        return legacy_event

    legacy_constraint = _resolve_node_id(influence.get(legacy_constraint_key), known_ids)
    if legacy_constraint:
        return legacy_constraint

    return ""


def _pick_founder_actor_id(actors: list[dict[str, Any]], case_id: str | None = None) -> str:
    if not actors:
        return ""

    def _score(actor: dict[str, Any]) -> int:
        actor_id = str(actor.get("id") or "").lower()
        actor_name = str(actor.get("name") or "").lower()
        actor_type = str(actor.get("type") or "").lower()
        score = 0
        if actor_type == "founder":
            score += 100
        if "founder" in actor_id or "founder" in actor_name:
            score += 60
        if actor_type == "company":
            score += 25
        if case_id:
            key = str(case_id).lower()
            if key and (key in actor_id or key in actor_name):
                score += 20
        return score

    best = max(actors, key=_score)
    return str(best.get("id") or "").strip()


def _build_founder_graph(founder_ontology: dict[str, Any], founder_events: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    case_meta = founder_ontology.get("meta") or {}
    case_id = str(case_meta.get("case_id") or "").strip() or None

    actors = founder_ontology.get("actors") or []
    actor_dicts = [item for item in actors if isinstance(item, dict)]
    founder_actor_id = _pick_founder_actor_id(actor_dicts, case_id=case_id)
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        actor_id = str(actor.get("id") or "").strip()
        if not actor_id:
            continue
        nodes.append(
            {
                "id": actor_id,
                "label": (
                    f"{str(actor.get('name') or actor_id)} (Founder)"
                    if actor_id == founder_actor_id
                    else str(actor.get("name") or actor_id)
                ),
                "node_type": "founder_actor" if actor_id == founder_actor_id else "actor",
                "is_founder": actor_id == founder_actor_id,
            }
        )

    products = founder_ontology.get("products") or []
    for product in products:
        if not isinstance(product, dict):
            continue
        product_id = str(product.get("id") or "").strip()
        if not product_id:
            continue
        nodes.append(
            {
                "id": product_id,
                "label": str(product.get("name") or product_id),
                "node_type": "product",
            }
        )

    for event in founder_events:
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        raw_text = str(event.get("event") or event.get("description") or "").strip()
        event_type = _normalize_event_type(event.get("type") or event.get("label") or event.get("event"), raw_text)
        nodes.append(
            {
                "id": event_id,
                "label": event_type or "other",
                "node_type": "event",
                "description": str(event.get("description") or raw_text).strip(),
            }
        )

        actor_ids = event.get("actors_involved") or []
        actor_ids = [str(item).strip() for item in actor_ids if str(item).strip()]

        for actor_id in actor_ids:
            edges.append(
                {
                    "source": actor_id,
                    "target": event_id,
                    "label": "involved_in",
                    "weight": 1.0,
                }
            )

    constraints = founder_ontology.get("constraints") or []
    for constraint in constraints:
        if not isinstance(constraint, dict):
            continue
        cid = str(constraint.get("id") or "").strip()
        if not cid:
            continue
        nodes.append(
            {
                "id": cid,
                "label": str(constraint.get("type") or constraint.get("category") or cid),
                "node_type": "constraint",
            }
        )

        applies_to = constraint.get("applies_to") or constraint.get("actors_affected") or []
        linked_founder = False
        for actor_id in applies_to:
            actor_token = str(actor_id).strip()
            if not actor_token:
                continue
            edges.append(
                {
                    "source": cid,
                    "target": actor_token,
                    "label": "constraints",
                    "weight": 1.0,
                }
            )
            if actor_token == founder_actor_id:
                linked_founder = True

        if founder_actor_id and not linked_founder:
            edges.append(
                {
                    "source": cid,
                    "target": founder_actor_id,
                    "label": "constraints",
                    "weight": 1.0,
                }
            )

    influences = founder_ontology.get("influences") or []
    known_node_ids = {node["id"] for node in nodes if isinstance(node, dict) and node.get("id")}
    for influence in influences:
        if not isinstance(influence, dict):
            continue
        source = _resolve_influence_endpoint(
            influence,
            primary_key="source",
            legacy_event_key="source_event",
            legacy_constraint_key="source_constraint",
            known_ids=known_node_ids,
        )
        target = _resolve_influence_endpoint(
            influence,
            primary_key="target",
            legacy_event_key="target_event",
            legacy_constraint_key="target_constraint",
            known_ids=known_node_ids,
        )
        if not source or not target:
            continue
        edges.append(
            {
                "source": source,
                "target": target,
                "label": str(influence.get("type") or "influences"),
                "weight": 1.0,
            }
        )

    node_ids = {node["id"] for node in nodes}
    dedup_nodes = []
    seen_nodes: set[str] = set()
    for node in nodes:
        node_id = node["id"]
        if node_id in seen_nodes:
            continue
        seen_nodes.add(node_id)
        dedup_nodes.append(node)

    dedup_edges = []
    seen_edges: set[tuple[str, str, str]] = set()
    for edge in edges:
        key = (str(edge["source"]), str(edge["target"]), str(edge.get("label") or ""))
        if key in seen_edges:
            continue
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            continue
        seen_edges.add(key)
        dedup_edges.append(edge)

    return {"nodes": dedup_nodes, "edges": dedup_edges}


def build_status_snapshot(
    *,
    strategy_ontology: dict[str, Any],
    founder_ontology: dict[str, Any],
    year: int | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    founder_events = _filter_founder_events(founder_ontology, year=year, date=date)
    timeline_events = _filter_strategy_events(strategy_ontology, year=year, date=date)
    if not timeline_events:
        timeline_events = _timeline_from_founder_events(founder_events)
    founder_graph = _build_founder_graph(founder_ontology, founder_events)

    return {
        "query": {
            "type": "status",
            "year": year,
            "date": date,
        },
        "timeline": timeline_events,
        "founder_graph": founder_graph,
        "summary": {
            "timeline_event_count": len(timeline_events),
            "founder_event_count": len(founder_events),
            "founder_node_count": len(founder_graph.get("nodes") or []),
            "founder_edge_count": len(founder_graph.get("edges") or []),
        },
    }
