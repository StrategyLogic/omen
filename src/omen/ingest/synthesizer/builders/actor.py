"""Build-time actor ontology extraction."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from omen.ingest.synthesizer.clients import invoke_json_prompt
from omen.ingest.synthesizer.prompts import build_actor_ontology_prompt
from omen.ingest.synthesizer.schema.actor import (
    ACTOR_TYPE_ALIAS,
    ALLOWED_ACTOR_TYPES,
    BACKGROUND_FACT_FIELDS,
    PRODUCT_TYPES,
    QUERY_TYPES,
    STRATEGIC_ACTOR_TYPES,
    STRATEGIC_ROLE_TOKENS,
    STRATEGIC_STYLE_FIELDS,
    VERSION,
)
from omen.ingest.models import CaseDocument, LLMConfig


def _display_name_from_case_id(case_id: str) -> str:
    tokens = [part for part in case_id.replace("_", "-").split("-") if part]
    if not tokens:
        return "Strategic Actor"
    return " ".join(token.capitalize() for token in tokens)


def _is_placeholder_name(value: str) -> bool:
    token = value.strip().lower()
    return token in {"strategic actor", "actor", "founder", "lead actor"}


def _normalize_role_label(value: Any) -> str:
    token = str(value or "").strip().lower().replace("_", " ")
    token = re.sub(r"\s*\([^)]*\)", "", token)
    token = re.sub(r"\s+", " ", token).strip(" -_,;:")
    return token or "actor"


def _default_background_facts() -> dict[str, Any]:
    defaults: dict[str, Any] = {field: [] for field in BACKGROUND_FACT_FIELDS}
    defaults["birth_year"] = None
    defaults["origin"] = None
    return defaults


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        token = value.strip()
        if token.isdigit():
            return int(token)
    return None


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip()
    return token or None


def _normalize_background_facts(background: Any) -> dict[str, Any]:
    facts = _default_background_facts()
    if not isinstance(background, dict):
        return facts

    for field in BACKGROUND_FACT_FIELDS:
        value = background.get(field)
        if field == "birth_year":
            facts[field] = _as_optional_int(value)
        elif field == "origin":
            facts[field] = _as_optional_str(value)
        else:
            facts[field] = _as_str_list(value)
    return facts


def _is_empty_fact_value(field: str, value: Any) -> bool:
    if field in {"birth_year", "origin"}:
        return value is None
    return not isinstance(value, list) or not value


def _merge_background_facts(primary: Any, fallback: Any) -> dict[str, Any]:
    merged = _normalize_background_facts(primary)
    fallback_facts = _normalize_background_facts(fallback)
    for field in BACKGROUND_FACT_FIELDS:
        if _is_empty_fact_value(field, merged.get(field)) and not _is_empty_fact_value(field, fallback_facts.get(field)):
            merged[field] = fallback_facts[field]
    return merged


def _normalize_strategic_style(profile: Any) -> dict[str, Any]:
    if not isinstance(profile, dict):
        return {
            "decision_style": None,
            "value_proposition": None,
            "decision_preferences": [],
            "non_negotiables": [],
        }

    source = profile.get("strategic_style")
    style = dict(source) if isinstance(source, dict) else {}

    if "decision_style" not in style:
        token = _as_optional_str(profile.get("decision_style") or profile.get("decision_making_style"))
        if token is not None:
            style["decision_style"] = token

    if "value_proposition" not in style:
        token = _as_optional_str(profile.get("value_proposition") or profile.get("strategic_value"))
        if token is not None:
            style["value_proposition"] = token

    if "decision_preferences" not in style:
        style["decision_preferences"] = _as_str_list(profile.get("decision_preferences"))

    if "non_negotiables" not in style:
        style["non_negotiables"] = _as_str_list(profile.get("non_negotiables"))

    normalized: dict[str, Any] = {}
    for field in STRATEGIC_STYLE_FIELDS:
        value = style.get(field)
        if field in {"decision_preferences", "non_negotiables"}:
            normalized[field] = _as_str_list(value)
        else:
            normalized[field] = _as_optional_str(value)
    return normalized


def _has_competitor_signal(*values: Any) -> bool:
    tokens = {
        "competitor",
        "competing",
        "alternative",
        "substitute",
        "project management",
        "collaboration",
        "process tool",
    }
    for value in values:
        text = str(value or "").strip().lower()
        if not text:
            continue
        if any(token in text for token in tokens):
            return True
    return False


def _slugify_id(value: str, *, fallback: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return token or fallback


def _normalize_product_identity(item: dict[str, Any], *, fallback_idx: int) -> tuple[str, str]:
    raw_id = str(item.get("id") or "").strip()
    raw_name = str(item.get("name") or "").strip()
    raw_type = str(item.get("type") or "").strip().lower()
    raw_desc = str(item.get("description") or "").strip()
    raw_role = str(item.get("role") or "").strip().lower()

    is_competitor = raw_type == "competitor" or _has_competitor_signal(raw_id, raw_name, raw_desc, raw_role)
    normalized_type = "competitor" if is_competitor else (raw_type if raw_type in PRODUCT_TYPES else "product")

    base = raw_id or raw_name
    base_slug = _slugify_id(base, fallback=f"item-{fallback_idx}")
    prefixes = (
        "actor-",
        "actor.",
        "actor_",
        "product-",
        "product.",
        "product_",
        "competitor-",
        "competitor.",
        "competitor_",
    )
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if base_slug.startswith(prefix):
                base_slug = base_slug[len(prefix) :]
                changed = True
                break
    base_slug = _slugify_id(base_slug, fallback=f"item-{fallback_idx}")

    normalized_prefix = "competitor" if normalized_type == "competitor" else "product"
    normalized_id = f"{normalized_prefix}-{base_slug}"
    return normalized_id, normalized_type


def _extract_profile(profile: Any) -> dict[str, Any]:
    background = profile.get("background_facts") if isinstance(profile, dict) else None
    # Some payloads still place factual background fields at profile root level.
    merged_background = _merge_background_facts(background, profile if isinstance(profile, dict) else None)
    extract_profile: dict[str, Any] = {
        "background_facts": merged_background
    }
    extract_profile["strategic_style"] = _normalize_strategic_style(profile)
    return extract_profile


def _extract_actor_profile(profile: Any) -> dict[str, Any] | None:
    if not isinstance(profile, dict):
        return None
    return dict(profile)


def _background_facts_all_empty(background_facts: dict[str, Any]) -> bool:
    for field in BACKGROUND_FACT_FIELDS:
        value = background_facts.get(field)
        if not _is_empty_fact_value(field, value):
            return False
    return True


def _event_facts_for_actor(events: list[dict[str, Any]], actor_id: str) -> list[str]:
    snippets: list[str] = []
    seen: set[str] = set()
    for event in events:
        involved = {str(item).strip() for item in (event.get("actors_involved") or []) if str(item).strip()}
        if actor_id not in involved:
            continue
        candidate = str(event.get("description") or event.get("name") or "").strip()
        if not candidate or candidate in seen:
            continue
        snippets.append(candidate)
        seen.add(candidate)
    return snippets[:5]


def _fallback_related_actors(events: list[dict[str, Any]], *, strategic_actor_id: str) -> list[dict[str, Any]]:
    related: list[dict[str, Any]] = []
    seen: set[str] = {strategic_actor_id}
    for event in events:
        for candidate in event.get("actors_involved") or []:
            actor_id = str(candidate or "").strip()
            if not actor_id or actor_id in seen:
                continue
            seen.add(actor_id)
            related.append(
                {
                    "id": actor_id,
                    "name": actor_id.replace("-", " ").replace("_", " ").title(),
                    "type": "Actor",
                    "role": "actor",
                }
            )
    return related


def _normalize_actor_kind_and_role(raw_type: Any, raw_role: Any = None) -> tuple[str, str]:
    type_token = str(raw_type or "").strip()
    role_token = _normalize_role_label(raw_role)
    lowered = type_token.lower()

    if type_token in {"Actor", "StrategicActor"}:
        role = role_token or ("strategic_actor" if type_token == "StrategicActor" else "actor")
        return type_token, role

    normalized_role = _normalize_role_label(ACTOR_TYPE_ALIAS.get(lowered, lowered or "actor"))
    if normalized_role in STRATEGIC_ROLE_TOKENS:
        return "StrategicActor", role_token or normalized_role
    return "Actor", role_token or normalized_role or "actor"


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

    strategic_actor_id = f"actor.{case_id}"
    actors = [
        {
            "id": strategic_actor_id,
            "name": _display_name_from_case_id(case_id),
            "type": "StrategicActor",
            "role": "founder",
            "profile": {"background_facts": _default_background_facts()},
        }
    ]
    actors.extend(_fallback_related_actors(events, strategic_actor_id=strategic_actor_id))

    return {
        "meta": {
            "version": VERSION,
            "case_id": case_id,
        },
        "actors": actors,
        "events": events,
        "influences": [],
        "query_skeleton": {"query_types": list(QUERY_TYPES)},
    }


def _to_actor_schema(payload: dict[str, Any], *, case_id: str) -> dict[str, Any]:
    version = VERSION

    actors_raw = payload.get("actors")
    actor_items = [item for item in actors_raw if isinstance(item, dict)] if isinstance(actors_raw, list) else []
    strategic_ids: set[str] = set()
    for actor in actor_items:
        actor_id = str(actor.get("id") or "").strip()
        actor_type, _actor_role = _normalize_actor_kind_and_role(actor.get("type"), actor.get("role"))
        if actor_id and actor_type == "StrategicActor":
            strategic_ids.add(actor_id)
            break

    actors: list[dict[str, Any]] = []
    for idx, actor in enumerate(actor_items, start=1):
        actor_id = str(actor.get("id") or f"actor-{idx}").strip() or f"actor-{idx}"
        actor_name = str(actor.get("name") or "").strip()
        actor_type, actor_role = _normalize_actor_kind_and_role(actor.get("type"), actor.get("role"))

        # Only the Strategic Actor carries profile content.
        if not strategic_ids and idx == 1:
            strategic_ids.add(actor_id)
        is_strategic_actor = actor_id in strategic_ids
        normalized_role = actor_role
        if is_strategic_actor and normalized_role in {"actor", "role"}:
            normalized_role = "founder"
        normalized_name = actor_name
        if is_strategic_actor and (not normalized_name or _is_placeholder_name(normalized_name)):
            normalized_name = _display_name_from_case_id(case_id)
        elif not normalized_name:
            normalized_name = f"Actor {idx}"

        actor_row: dict[str, Any] = {
            "id": actor_id,
            "name": normalized_name,
            "type": "StrategicActor" if is_strategic_actor else "Actor",
            "role": normalized_role,
        }
        if is_strategic_actor:
            actor_row["profile"] = _extract_profile(actor.get("profile"))
        else:
            actor_profile = _extract_actor_profile(actor.get("profile"))
            if actor_profile is not None:
                actor_row["profile"] = actor_profile
        actors.append(actor_row)
    if not actors:
        actors = [
            {
                "id": f"actor.{case_id}",
                "name": _display_name_from_case_id(case_id),
                "type": "StrategicActor",
                "role": "founder",
                "profile": {"background_facts": _default_background_facts()},
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

    for actor in actors:
        if str(actor.get("type") or "") != "StrategicActor":
            continue
        profile = actor.get("profile")
        if not isinstance(profile, dict):
            continue
        background_facts = profile.get("background_facts")
        if not isinstance(background_facts, dict):
            continue
        if not _background_facts_all_empty(background_facts):
            continue
        actor_id = str(actor.get("id") or "").strip()
        if not actor_id:
            continue
        inferred_experiences = _event_facts_for_actor(events, actor_id)
        if inferred_experiences:
            background_facts["key_experiences"] = inferred_experiences

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
        },
        "actors": actors,
        "events": events,
        "products": products,
        "influences": influences,
        "query_skeleton": {"query_types": list(QUERY_TYPES)},
    }


def _as_product_node(actor: dict[str, Any]) -> dict[str, Any]:
    item_name = str(actor.get("name") or actor.get("id") or "product").strip() or "product"
    item_id, item_type = _normalize_product_identity(actor, fallback_idx=1)
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
    next_products: list[dict[str, Any]] = []
    product_ids: set[str] = set()
    product_id_alias: dict[str, str] = {}

    for idx, product in enumerate(product_items, start=1):
        normalized_product = _as_product_node(product)
        normalized_id, normalized_type = _normalize_product_identity(product, fallback_idx=idx)
        old_id = str(product.get("id") or "").strip()
        normalized_product["id"] = normalized_id
        normalized_product["type"] = normalized_type
        if old_id and old_id != normalized_id:
            product_id_alias[old_id] = normalized_id
        if normalized_id in product_ids:
            continue
        product_ids.add(normalized_id)
        next_products.append(normalized_product)

    for actor in actor_items:
        actor_id = str(actor.get("id") or "").strip()
        actor_name = str(actor.get("name") or "").strip().lower()
        actor_type_raw = str(actor.get("type") or "organization").strip().lower()
        actor_type = ACTOR_TYPE_ALIAS.get(actor_type_raw, actor_type_raw)

        actor_role = _normalize_role_label(actor.get("role"))
        is_product_like = (
            actor_type in PRODUCT_TYPES
            or any(token in actor_name for token in ("product", "platform", "tool", "saas", "app"))
        )
        if is_product_like:
            inferred_type = "competitor" if _has_competitor_signal(actor_id, actor_name, actor_role, actor_type) else actor_type
            product_candidate = {**actor, "type": inferred_type}
            product_node = _as_product_node(product_candidate)
            normalized_id, normalized_type = _normalize_product_identity(product_candidate, fallback_idx=len(next_products) + 1)
            product_node["id"] = normalized_id
            product_node["type"] = normalized_type
            if actor_id and actor_id != normalized_id:
                product_id_alias[actor_id] = normalized_id
            if normalized_id not in product_ids:
                next_products.append(product_node)
                product_ids.add(normalized_id)
            continue

        normalized_type = actor_type if actor_type in ALLOWED_ACTOR_TYPES else "role"
        next_actor = dict(actor)
        next_actor["type"] = normalized_type
        
        next_actors.append(next_actor)

    query_skeleton = normalized.get("query_skeleton")
    if not isinstance(query_skeleton, dict):
        query_skeleton = {}
    query_skeleton["query_types"] = list(QUERY_TYPES)

    if not next_products:
        default_product = _infer_default_product(case_doc)
        if default_product is not None:
            normalized_id, normalized_type = _normalize_product_identity(default_product, fallback_idx=1)
            default_product["id"] = normalized_id
            default_product["type"] = normalized_type
            next_products.append(default_product)
            product_ids.add(normalized_id)

    founder_actor_id = ""
    for actor in next_actors:
        actor_id = str(actor.get("id") or "").strip()
        actor_type = str(actor.get("type") or "").strip().lower()
        actor_name = str(actor.get("name") or "").strip().lower()
        if not actor_id:
            continue
        if actor_type in STRATEGIC_ACTOR_TYPES or any(
            token in actor_name or token in actor_id.lower()
            for token in ("founder", "ceo", "top management", "top_management")
        ):
            founder_actor_id = actor_id
            break
    if not founder_actor_id and next_actors:
        founder_actor_id = str(next_actors[0].get("id") or "").strip()

    product_type_by_id = {
        str(item.get("id") or "").strip(): str(item.get("type") or "").strip().lower()
        for item in next_products
        if str(item.get("id") or "").strip()
    }

    influences = normalized.get("influences")
    influence_items = [item for item in influences if isinstance(item, dict)] if isinstance(influences, list) else []
    remapped_influences: list[dict[str, Any]] = []
    for influence in influence_items:
        source = str(influence.get("source") or "").strip()
        target = str(influence.get("target") or "").strip()
        source = product_id_alias.get(source, source)
        target = product_id_alias.get(target, target)
        remapped = dict(influence)
        if source:
            remapped["source"] = source
        if target:
            remapped["target"] = target
        remapped_influences.append(remapped)
    cleaned_influences: list[dict[str, Any]] = []
    for influence in remapped_influences:
        source = str(influence.get("source") or "").strip()
        target = str(influence.get("target") or "").strip()
        relation = str(influence.get("type") or "").strip().lower()
        if founder_actor_id and source == founder_actor_id and product_type_by_id.get(target) == "competitor" and relation == "builds":
            continue
        cleaned_influences.append(influence)
    influence_items = cleaned_influences
    seen_edges = {
        (
            str(item.get("source") or "").strip(),
            str(item.get("target") or "").strip(),
            str(item.get("type") or "").strip(),
        )
        for item in influence_items
    }
    if founder_actor_id:
        for product in next_products:
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
        core_products = [p for p in next_products if str(p.get("type")).lower() != "competitor"]
        competitors = [p for p in next_products if str(p.get("type")).lower() == "competitor"]
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
    normalized["products"] = next_products
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
        payload = invoke_json_prompt(
            user_prompt=prompt,
            config=config,
            stage="actor_ontology_prompt",
            expected_type="object",
        )
        if payload:
            if not isinstance(payload, dict):
                raise ValueError("actor payload is not a JSON object")
            return _normalize_founder_payload(payload, case_doc)
    except Exception:
        pass

    return _default_actor(case_doc.case_id, timeline_events)


def actor_hash(actor_ontology: dict[str, Any]) -> str:
    canonical = json.dumps(actor_ontology, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
