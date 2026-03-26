"""Semantic enhancement for non-founder actor decision relationships.

Rules:
- Exclude founder actor from enhancement.
- Build semantic relations only from actor co-involvement in decision events.
- Do not use constraints to generate enhancement relations.
"""

from __future__ import annotations

import json
from typing import Any

from omen.ingest.llm_ontology.clients import create_chat_client
from omen.ingest.llm_ontology.prompts import build_actor_semantic_enhancement_prompt
from omen.models.case_replay_models import LLMConfig


def _find_founder_actor_id(actors: list[dict[str, Any]]) -> str:
    for actor in actors:
        actor_id = str(actor.get("id") or "").strip()
        actor_name = str(actor.get("name") or "").lower()
        actor_role = str(actor.get("role") or "").lower()
        actor_type = str(actor.get("type") or "").lower()
        if not actor_id:
            continue
        if actor_role == "founder" or actor_type == "founder":
            return actor_id
        if "founder" in actor_name or "founder" in actor_id.lower():
            return actor_id
    def _score(actor: dict[str, Any]) -> int:
        actor_id = str(actor.get("id") or "").lower()
        actor_name = str(actor.get("name") or "").lower()
        actor_role = str(actor.get("role") or "").lower()
        actor_type = str(actor.get("type") or "").lower()
        score = 0
        if actor_role == "founder" or actor_type == "founder":
            score += 100
        if "founder" in actor_name or "founder" in actor_id:
            score += 80
        if actor_type in {"company", "organization", "startup"}:
            score += 40
        if "team" in actor_name or "team" in actor_id:
            score += 20
        return score

    if not actors:
        return ""
    best = max(actors, key=_score)
    best_id = str(best.get("id") or "").strip()
    return best_id


def _add_relation(
    relations: list[dict[str, Any]],
    seen: set[tuple[str, str]],
    *,
    source: str,
    target: str,
    relation_type: str,
    description: str,
    evidence_refs: list[str] | None = None,
) -> bool:
    # Key change: We block ANY new relation between two nodes that ALREADY have a relationship
    # This prevents synonyms like (A, B, "influences") and (A, B, "pressures")
    key = (source, target)
    if key in seen:
        return False
    seen.add(key)
    relations.append(
        {
            "source": source,
            "target": target,
            "type": relation_type,
            "description": description,
            "evidence_refs": list(evidence_refs or []),
            "origin": "semantic_enhancement",
        }
    )
    return True


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    payload = json.loads(text[start : end + 1])
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _normalize_relation_keys(item: dict[str, Any]) -> dict[str, Any]:
    relation = dict(item)
    if "source" not in relation and "from" in relation:
        relation["source"] = relation.pop("from")
    if "target" not in relation and "to" in relation:
        relation["target"] = relation.pop("to")
    return relation


def enhance_actor_decision_relationships(
    founder_ontology: dict[str, Any],
    *,
    config: LLMConfig | None = None,
) -> tuple[dict[str, Any], int]:
    payload = dict(founder_ontology)
    actors = payload.get("actors") or []
    products = payload.get("products") or []
    actor_dicts = [actor for actor in actors if isinstance(actor, dict)]
    product_dicts = [product for product in products if isinstance(product, dict)]
    actor_ids = [str(actor.get("id") or "").strip() for actor in actor_dicts]
    actor_ids = [actor_id for actor_id in actor_ids if actor_id]

    # Combine actors and products for semantic analysis
    # Many products might be competitors that influence strategic choices
    competitor_product_ids = {
        str(p.get("id") or "").strip() 
        for p in product_dicts 
        if str(p.get("type") or "").lower() == "competitor"
    }

    founder_actor_id = _find_founder_actor_id(actor_dicts)
    
    # 0. Exclude Founder from analysis candidates
    candidate_actor_ids = {aid for aid in actor_ids if aid != founder_actor_id}
    
    # Combined entity pool for analysis (Excluded-Founder Actors + Competitor Products)
    all_entity_ids = candidate_actor_ids | competitor_product_ids

    influences = payload.get("influences") or []
    relations: list[dict[str, Any]] = []
    
    # Collect existing relations for exclusion in prompt
    existing_simple_rels = []
    seen: set[tuple[str, str]] = set()

    for item in influences:
        if not isinstance(item, dict):
            continue
        rel = _normalize_relation_keys(item)
        relations.append(rel)
        
        src = str(rel.get("source") or "").strip()
        tgt = str(rel.get("target") or "").strip()
        rtype = str(rel.get("type") or "").strip()
        if src and tgt:
            # We track (src, tgt) to block any additional semantic link between them
            seen.add((src, tgt))
            # Even if founder is in existing, we still pass it to list for exclusion
            existing_simple_rels.append({"source": src, "target": tgt, "type": rtype})

    added_count = 0

    if config and len(all_entity_ids) >= 2:
        # Prepare payload: STRICTLY non-founder actors + competitor products
        analysis_payload = []
        for actor in actor_dicts:
            aid = str(actor.get("id") or "").strip()
            if aid in candidate_actor_ids:
                analysis_payload.append({
                    "id": aid,
                    "name": str(actor.get("name") or "").strip(),
                    "type": str(actor.get("type") or "").strip(),
                    "description": str(actor.get("description") or "").strip(),
                })
        
        for product in product_dicts:
            pid = str(product.get("id") or "").strip()
            if pid in competitor_product_ids:
                analysis_payload.append({
                    "id": pid,
                    "name": str(product.get("name") or "").strip(),
                    "type": "competitor_product",
                    "description": str(product.get("description") or "").strip(),
                })

        prompt = build_actor_semantic_enhancement_prompt(
            json.dumps(analysis_payload, ensure_ascii=False),
            json.dumps(existing_simple_rels, ensure_ascii=False)
        )

        try:
            chat = create_chat_client(config)
            response = chat.invoke(prompt)
            content = response.content if isinstance(response.content, str) else json.dumps(response.content)
            generated = _extract_json_array(content)
            for item in generated:
                relation = _normalize_relation_keys(item)
                source = str(relation.get("source") or "").strip()
                target = str(relation.get("target") or "").strip()
                relation_type = str(relation.get("type") or "").strip() or "influences"
                description = str(relation.get("description") or "").strip()
                evidence_refs = relation.get("evidence_refs") or []
                
                # Validation rules:
                # 1. Source/Target must be in the entity pool (no Founder)
                if source not in all_entity_ids or target not in all_entity_ids:
                    continue
                
                # 2. COMPETITOR product ONLY points outward (influences/pressures others)
                if source in competitor_product_ids and target in competitor_product_ids:
                   # Skip competitor-to-competitor for now or keep if strategic
                   pass

                if source == target:
                    continue

                added = _add_relation(
                    relations,
                    seen,
                    source=source,
                    target=target,
                    relation_type=relation_type,
                    description=description,
                    evidence_refs=[str(item) for item in evidence_refs],
                )
                if added:
                    added_count += 1
        except Exception:
            pass

    payload["influences"] = relations
    meta = payload.get("meta") or {}
    meta["actor_semantic_enhanced"] = True
    meta["actor_semantic_relations_added"] = added_count
    payload["meta"] = meta
    return payload, added_count
