"""Build-time actor ontology extraction."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from omen.ingest.llm_ontology.clients import create_chat_client
from omen.ingest.llm_ontology.prompts import build_actor_ontology_prompt
from omen.ingest.schema.actor_schema import (
    DISCLOSURE_LEVEL,
    QUERY_TYPES,
    REDACTION_MARKER,
    STRATEGIC_DIMENSIONS,
    VERSION,
)
from omen.ingest.models.case_models import CaseDocument, LLMConfig


_PRODUCT_TYPES = {"product", "platform", "tool", "saas", "app", "system"}
_ACTOR_TYPE_ALIAS = {
    "company": "organization",
    "startup": "organization",
    "enterprise": "organization",
    "business": "organization",
    "org": "organization",
    "department": "team",
    "squad": "team",
    "group": "team",
    "top management": "top_management",
    "top-management": "top_management",
    "executive": "top_management",
    "management": "top_management",
}
_ALLOWED_ACTOR_TYPES = {
    "founder",
    "ceo",
    "top_management",
    "person",
    "team",
    "organization",
    "customer",
    "partner",
    "investor",
    "regulator",
    "competitor",
    "role",
}
_STRATEGIC_ACTOR_TYPES = {"founder", "ceo", "top_management"}


def _extract_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response does not contain a JSON object")
    payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("actor payload is not a JSON object")
    return payload


def _default_actor(case_id: str, timeline_events: list[dict[str, Any]]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for index, event in enumerate(timeline_events[:5], start=1):
        event_id = str(event.get("id") or f"event-{index}").strip() or f"event-{index}"
        events.append(
            {
                "id": event_id,
                "name": str(event.get("name") or event.get("event") or event_id),
                "type": str(event.get("type") or "event"),
                "date": str(event.get("time") or "unknown"),
                "description": str(event.get("description") or event.get("event") or "unknown"),
            }
        )

    return {
        "meta": {
            "version": VERSION,
            "case_id": case_id,
            "disclosure_level": DISCLOSURE_LEVEL,
            "strategic_dimensions": list(STRATEGIC_DIMENSIONS),
        },
        "actors": [
            {
                "id": f"actor.{case_id}",
                "name": "Strategic Actor",
                "type": "founder",
                "profile": {
                        "mental_patterns": dict(REDACTION_MARKER),
                        "strategic_style": dict(REDACTION_MARKER),
                },
            }
        ],
        "events": events,
        "influences": [],
        "query_skeleton": {"query_types": list(QUERY_TYPES)},
    }


def _to_actor_schema(payload: dict[str, Any], *, case_id: str) -> dict[str, Any]:
    meta = payload.get("meta") or {}
    version = str(meta.get("version") or "").strip()
    if not version:
        version = VERSION
    elif not version.endswith("-public"):
        version = f"{version}-public"

    actors_raw = payload.get("actors")
    actor_items = [item for item in actors_raw if isinstance(item, dict)] if isinstance(actors_raw, list) else []
    strategic_ids: set[str] = set()
    for actor in actor_items:
        actor_id = str(actor.get("id") or "").strip()
        actor_name = str(actor.get("name") or "").strip().lower()
        actor_type_raw = str(actor.get("type") or "role").strip().lower()
        actor_type = _ACTOR_TYPE_ALIAS.get(actor_type_raw, actor_type_raw)
        if actor_id and (
            actor_type in _STRATEGIC_ACTOR_TYPES
            or any(token in actor_name for token in ("founder", "ceo", "top management", "top_management"))
        ):
            strategic_ids.add(actor_id)
            break

    actors: list[dict[str, Any]] = []
    for idx, actor in enumerate(actor_items, start=1):
        actor_id = str(actor.get("id") or f"actor-{idx}").strip() or f"actor-{idx}"
        actor_name = str(actor.get("name") or "Strategic Actor").strip() or "Strategic Actor"
        actor_type_raw = str(actor.get("type") or "role").strip().lower() or "role"
        actor_type = _ACTOR_TYPE_ALIAS.get(actor_type_raw, actor_type_raw)
        if actor_type not in _ALLOWED_ACTOR_TYPES:
            actor_type = "role"

        # Only the Strategic Actor carries strategic mental-pattern profile.
        if not strategic_ids and idx == 1:
            strategic_ids.add(actor_id)
        is_strategic_actor = actor_id in strategic_ids

        actor_row: dict[str, Any] = {
            "id": actor_id,
            "name": actor_name,
            "type": actor_type if is_strategic_actor else "role",
        }
        if is_strategic_actor:
            actor_row["profile"] = {
                "mental_patterns": dict(REDACTION_MARKER),
                "strategic_style": dict(REDACTION_MARKER),
            }
        actors.append(actor_row)
    if not actors:
        actors = [
            {
                "id": f"actor.{case_id}",
                "name": "Strategic Actor",
                "type": "role",
                "profile": {
                    "mental_patterns": dict(REDACTION_MARKER),
                    "strategic_style": dict(REDACTION_MARKER),
                },
            }
        ]

    events_raw = payload.get("events")
    event_items = [item for item in events_raw if isinstance(item, dict)] if isinstance(events_raw, list) else []
    events: list[dict[str, Any]] = []
    for idx, event in enumerate(event_items, start=1):
        event_id = str(event.get("id") or f"event-{idx}").strip() or f"event-{idx}"
        actor_refs = [str(item).strip() for item in (event.get("actors_involved") or []) if str(item).strip()]
        evidence_refs = [str(item).strip() for item in (event.get("evidence_refs") or []) if str(item).strip()]
        events.append(
            {
                "id": event_id,
                "name": str(event.get("name") or event.get("event") or event_id),
                "type": str(event.get("type") or "event"),
                "date": str(event.get("date") or event.get("time") or "unknown"),
                "description": str(event.get("description") or event.get("event") or "unknown"),
                "actors_involved": actor_refs,
                "evidence_refs": evidence_refs,
                "is_strategy_related": bool(event.get("is_strategy_related", True)),
            }
        )

    products_raw = payload.get("products")
    product_items = [item for item in products_raw if isinstance(item, dict)] if isinstance(products_raw, list) else []
    products: list[dict[str, Any]] = []
    for idx, product in enumerate(product_items, start=1):
        product_id = str(product.get("id") or f"product-{idx}").strip() or f"product-{idx}"
        products.append(
            {
                "id": product_id,
                "name": str(product.get("name") or product_id),
                "type": str(product.get("type") or "product").strip().lower() or "product",
                "description": str(product.get("description") or "").strip(),
                "attributes": product.get("attributes") if isinstance(product.get("attributes"), dict) else {},
            }
        )

    constraints_raw = payload.get("constraints")
    constraint_items = [item for item in constraints_raw if isinstance(item, dict)] if isinstance(constraints_raw, list) else []
    constraints: list[dict[str, Any]] = []
    for idx, constraint in enumerate(constraint_items, start=1):
        constraint_id = str(constraint.get("id") or f"constraint-{idx}").strip() or f"constraint-{idx}"
        applies_to = [str(item).strip() for item in (constraint.get("applies_to") or constraint.get("actors_affected") or []) if str(item).strip()]
        constraints.append(
            {
                "id": constraint_id,
                "type": str(constraint.get("type") or constraint.get("name") or "constraint").strip() or "constraint",
                "category": str(constraint.get("category") or "").strip(),
                "applies_to": applies_to,
            }
        )

    influences_raw = payload.get("influences")
    influence_items = [item for item in influences_raw if isinstance(item, dict)] if isinstance(influences_raw, list) else []
    influences: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    for influence in influence_items:
        source = str(influence.get("source") or influence.get("source_event") or influence.get("source_constraint") or "").strip()
        target = str(influence.get("target") or influence.get("target_event") or influence.get("target_constraint") or "").strip()
        relation = str(influence.get("type") or "influences").strip() or "influences"
        if not source or not target:
            continue
        key = (source, target, relation)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        influences.append(
            {
                "source": source,
                "target": target,
                "type": relation,
                "description": str(influence.get("description") or "").strip(),
            }
        )

    return {
        "meta": {
            "version": version,
            "case_id": case_id,
            "disclosure_level": DISCLOSURE_LEVEL,
            "strategic_dimensions": list(STRATEGIC_DIMENSIONS),
        },
        "actors": actors,
        "events": events,
        "products": products,
        "constraints": constraints,
        "influences": influences,
        "query_skeleton": {"query_types": list(QUERY_TYPES)},
    }


def _as_product_node(actor: dict[str, Any]) -> dict[str, Any]:
    item_id = str(actor.get("id") or "").strip()
    item_name = str(actor.get("name") or item_id or "product").strip() or "product"
    item_type = str(actor.get("type") or "product").strip().lower() or "product"
    return {
        "id": item_id,
        "name": item_name,
        "type": item_type,
        "description": str(actor.get("description") or "").strip(),
        "attributes": actor.get("attributes") if isinstance(actor.get("attributes"), dict) else {},
    }


def _infer_default_product(case_doc: CaseDocument) -> dict[str, Any] | None:
    text = case_doc.raw_text.lower()
    if not any(token in text for token in ("product", "platform", "tool", "saas", "software")):
        return None

    base_name = case_doc.title.replace("Replay", "").strip(" -_")
    if "/" in base_name:
        base_name = base_name.split("/", 1)[0].strip()
    if not base_name:
        base_name = case_doc.case_id.replace("-", " ").title()

    product_id = f"product-{case_doc.case_id}".replace("_", "-")
    return {
        "id": product_id,
        "name": base_name,
        "type": "platform",
        "description": f"Core product/platform asset for case {case_doc.case_id}.",
        "attributes": {},
    }


def _normalize_founder_payload(payload: dict[str, Any], case_doc: CaseDocument) -> dict[str, Any]:
    normalized = dict(payload)
    actors = normalized.get("actors")
    products = normalized.get("products")
    actor_items = [item for item in actors if isinstance(item, dict)] if isinstance(actors, list) else []
    product_items = [item for item in products if isinstance(item, dict)] if isinstance(products, list) else []

    next_actors: list[dict[str, Any]] = []
    product_ids = {str(item.get("id") or "").strip() for item in product_items if str(item.get("id") or "").strip()}

    for actor in actor_items:
        actor_id = str(actor.get("id") or "").strip()
        actor_name = str(actor.get("name") or "").strip().lower()
        actor_type_raw = str(actor.get("type") or "organization").strip().lower()
        actor_type = _ACTOR_TYPE_ALIAS.get(actor_type_raw, actor_type_raw)

        is_product_like = (
            actor_type in _PRODUCT_TYPES
            or any(token in actor_name for token in ("product", "platform", "tool", "saas", "app"))
        )
        if is_product_like:
            product_node = _as_product_node({**actor, "type": actor_type})
            if actor_id and actor_id not in product_ids:
                product_items.append(product_node)
                product_ids.add(actor_id)
            continue

        normalized_type = actor_type if actor_type in _ALLOWED_ACTOR_TYPES else "role"
        next_actor = dict(actor)
        next_actor["type"] = normalized_type
        
        next_actors.append(next_actor)

    query_skeleton = normalized.get("query_skeleton")
    if not isinstance(query_skeleton, dict):
        query_skeleton = {}
    query_skeleton["query_types"] = list(QUERY_TYPES)

    if not product_items:
        default_product = _infer_default_product(case_doc)
        if default_product is not None:
            product_items.append(default_product)

    founder_actor_id = ""
    for actor in next_actors:
        actor_id = str(actor.get("id") or "").strip()
        actor_type = str(actor.get("type") or "").strip().lower()
        actor_name = str(actor.get("name") or "").strip().lower()
        if not actor_id:
            continue
        if actor_type in _STRATEGIC_ACTOR_TYPES or any(
            token in actor_name or token in actor_id.lower()
            for token in ("founder", "ceo", "top management", "top_management")
        ):
            founder_actor_id = actor_id
            break
    if not founder_actor_id and next_actors:
        founder_actor_id = str(next_actors[0].get("id") or "").strip()

    influences = normalized.get("influences")
    influence_items = [item for item in influences if isinstance(item, dict)] if isinstance(influences, list) else []
    seen_edges = {
        (
            str(item.get("source") or "").strip(),
            str(item.get("target") or "").strip(),
            str(item.get("type") or "").strip(),
        )
        for item in influence_items
    }
    if founder_actor_id:
        for product in product_items:
            product_id = str(product.get("id") or "").strip()
            product_type = str(product.get("type") or "").strip().lower()
            if not product_id:
                continue

            if product_type == "competitor":
                # Competitor influences/constrains the founder/actors
                key = (product_id, founder_actor_id, "influences")
                if key not in seen_edges:
                    influence_items.append(
                        {
                            "source": product_id,
                            "target": founder_actor_id,
                            "type": "influences",
                            "description": "Competitor market presence influences founder strategic decisions.",
                        }
                    )
                    seen_edges.add(key)
            else:
                # Founder builds core products
                key = (founder_actor_id, product_id, "builds")
                if key not in seen_edges:
                    influence_items.append(
                        {
                            "source": founder_actor_id,
                            "target": product_id,
                            "type": "builds",
                            "description": "Founder/lead actor builds and steers the core product asset.",
                        }
                    )
                    seen_edges.add(key)

        # Cross-link: Product competes with Competitor
        core_products = [p for p in product_items if str(p.get("type")).lower() != "competitor"]
        competitors = [p for p in product_items if str(p.get("type")).lower() == "competitor"]
        for cp in core_products:
            for comp in competitors:
                cp_id = str(cp.get("id"))
                comp_id = str(comp.get("id"))
                key = (cp_id, comp_id, "competes_with")
                if key not in seen_edges:
                    influence_items.append({
                        "source": cp_id,
                        "target": comp_id,
                        "type": "competes_with",
                        "description": "Core product competes with traditional solutions."
                    })
                    seen_edges.add(key)

        # Link actors to events they participate in
        for event in normalized.get("events", []):
            event_id = str(event.get("id"))
            for actor_involved_id in event.get("actors_involved", []):
                key = (str(actor_involved_id), event_id, "participates_in")
                if key not in seen_edges:
                    influence_items.append({
                        "source": str(actor_involved_id),
                        "target": event_id,
                        "type": "participates_in",
                        "description": "Actor participates in strategic decision/event."
                    })
                    seen_edges.add(key)
            
            # Event -> affects -> Core Product
            # By default, linking strategic decisions to all core products if not specified
            for cp in core_products:
                cp_id = str(cp.get("id"))
                key = (event_id, cp_id, "affects")
                if key not in seen_edges:
                    influence_items.append({
                        "source": event_id,
                        "target": cp_id,
                        "type": "affects",
                        "description": "Strategic decision affects the core product lifecycle."
                    })
                    seen_edges.add(key)

    normalized["actors"] = next_actors
    normalized["products"] = product_items
    normalized["influences"] = influence_items
    normalized["query_skeleton"] = query_skeleton
    return _to_actor_schema(normalized, case_id=case_doc.case_id)


def extract_actor_ontology(
    *,
    case_doc: CaseDocument,
    chunks: list[str],
    config: LLMConfig,
    timeline_events: list[dict[str, Any]],
) -> dict[str, Any]:
    excerpt = "\n\n---\n\n".join(chunks[: min(len(chunks), config.max_chunks)])
    timeline_json = json.dumps(timeline_events[:20], ensure_ascii=False)
    prompt = build_actor_ontology_prompt(case_doc, excerpt, timeline_json)

    try:
        chat = create_chat_client(config)
        response = chat.invoke(prompt)
        content = response.content if isinstance(response.content, str) else json.dumps(response.content)
        payload = _extract_json_object(content)
        if payload:
            return _normalize_founder_payload(payload, case_doc)
    except Exception:
        pass

    return _default_actor(case_doc.case_id, timeline_events)


def actor_hash(actor_ontology: dict[str, Any]) -> str:
    canonical = json.dumps(actor_ontology, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
