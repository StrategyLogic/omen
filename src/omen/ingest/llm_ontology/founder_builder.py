"""Build-time founder ontology extraction for case replay."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from omen.ingest.llm_ontology.clients import create_chat_client
from omen.ingest.llm_ontology.prompts import build_founder_ontology_prompt
from omen.models.case_replay_models import CaseDocument, LLMConfig


_DEF_QUERY_TYPES = ["status", "why", "persona"]
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
}
_ALLOWED_ACTOR_TYPES = {
    "founder",
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


def _extract_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response does not contain a JSON object")
    payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("founder payload is not a JSON object")
    return payload


def _default_founder(case_id: str, timeline_events: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_refs: list[str] = []
    for event in timeline_events:
        refs = event.get("evidence_refs")
        if isinstance(refs, list):
            evidence_refs.extend(str(item) for item in refs)

    return {
        "meta": {
            "version": "1.0.0",
            "case_id": case_id,
            "slice": "founder",
            "generated_at": "fallback",
        },
        "actors": [
            {
                "id": f"founder.{case_id}",
                "shared_id": f"actor:founder:{case_id}",
                "role": "founder",
                "name": "Founder",
                "assignments": [{"title": "founder", "start_date": "unknown", "end_date": None}],
                "traits": [],
                "evidence_refs": evidence_refs[:3],
            }
        ],
        "products": [],
        "events": [
            {
                "id": f"founder.{event.get('id', 'event')}",
                "type": "decision",
                "date": str(event.get("time") or "unknown"),
                "impact_score": float(event.get("confidence") or 0.5),
                "related": [],
                "evidence_refs": event.get("evidence_refs") if isinstance(event.get("evidence_refs"), list) else [],
                "decision": {
                    "content": str(event.get("description") or event.get("event") or "unknown"),
                    "alternatives": [],
                    "aligned_intent": "unknown",
                    "response_to": [],
                    "outcome": "unknown",
                },
            }
            for event in timeline_events[:5]
        ],
        "constraints": [],
        "influences": [
            {
                "source": f"founder.{case_id}",
                "targets": ["tech", "market"],
                "weight": 0.6,
                "nature": "shaper",
                "rationale": "derived from historical founder decisions",
                "evidence_refs": evidence_refs[:5],
            }
        ],
        "query_skeleton": {
            "query_types": _DEF_QUERY_TYPES,
            "base_context": ["actors", "events", "constraints", "influences"],
            "evidence_bundle": evidence_refs[:10],
        },
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

        normalized_type = actor_type if actor_type in _ALLOWED_ACTOR_TYPES else "organization"
        next_actor = dict(actor)
        next_actor["type"] = normalized_type
        next_actors.append(next_actor)

    query_skeleton = normalized.get("query_skeleton")
    if not isinstance(query_skeleton, dict):
        query_skeleton = {}
    query_skeleton["query_types"] = _DEF_QUERY_TYPES

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
        if actor_type == "founder" or "founder" in actor_name or "founder" in actor_id.lower():
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
            if not product_id:
                continue
            key = (founder_actor_id, product_id, "builds")
            if key in seen_edges:
                continue
            influence_items.append(
                {
                    "source": founder_actor_id,
                    "target": product_id,
                    "type": "builds",
                    "description": "Founder/lead actor builds and steers the core product asset.",
                    "origin": "normalization",
                }
            )
            seen_edges.add(key)

    normalized["actors"] = next_actors
    normalized["products"] = product_items
    normalized["influences"] = influence_items
    normalized["query_skeleton"] = query_skeleton
    return normalized


def extract_founder_ontology(
    *,
    case_doc: CaseDocument,
    chunks: list[str],
    config: LLMConfig,
    timeline_events: list[dict[str, Any]],
) -> dict[str, Any]:
    excerpt = "\n\n---\n\n".join(chunks[: min(len(chunks), config.max_chunks)])
    timeline_json = json.dumps(timeline_events[:20], ensure_ascii=False)
    prompt = build_founder_ontology_prompt(case_doc, excerpt, timeline_json)

    try:
        chat = create_chat_client(config)
        response = chat.invoke(prompt)
        content = response.content if isinstance(response.content, str) else json.dumps(response.content)
        payload = _extract_json_object(content)
        if payload:
            return _normalize_founder_payload(payload, case_doc)
    except Exception:
        pass

    return _default_founder(case_doc.case_id, timeline_events)


def founder_hash(founder_ontology: dict[str, Any]) -> str:
    canonical = json.dumps(founder_ontology, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
