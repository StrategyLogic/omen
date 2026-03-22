"""Build-time founder ontology extraction for case replay."""

from __future__ import annotations

import hashlib
import json
from textwrap import dedent
from typing import Any

from omen.ingest.llm_ontology.clients import create_chat_client
from omen.models.case_replay_models import CaseDocument, LLMConfig


_DEF_QUERY_TYPES = ["status", "why", "persona"]


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


def extract_founder_ontology(
    *,
    case_doc: CaseDocument,
    chunks: list[str],
    config: LLMConfig,
    timeline_events: list[dict[str, Any]],
) -> dict[str, Any]:
    excerpt = "\n\n---\n\n".join(chunks[: min(len(chunks), config.max_chunks)])
    timeline_json = json.dumps(timeline_events[:20], ensure_ascii=False)

    prompt = dedent(
        f"""
        You are an ontology extraction assistant.
        Build founder_ontology JSON only.

        Required top-level keys:
        - meta
        - actors
        - events
        - constraints
        - influences
        - query_skeleton

        Required constraints:
        - meta includes version/case_id/slice/generated_at
        - events must use time evidence from timeline input
        - events should include short type labels for graph display (e.g. launch/release/pilot)
        - keep long narrative in description fields when available
        - do not use phase/stage field
        - query_skeleton.query_types must be: status, why, persona

        Case ID: {case_doc.case_id}
        Title: {case_doc.title}
        Known outcome: {case_doc.known_outcome}

        Timeline events (JSON):
        {timeline_json}

        Source excerpt:
        {excerpt}
        """
    ).strip()

    try:
        chat = create_chat_client(config)
        response = chat.invoke(prompt)
        content = response.content if isinstance(response.content, str) else json.dumps(response.content)
        payload = _extract_json_object(content)
        if payload:
            return payload
    except Exception:
        pass

    return _default_founder(case_doc.case_id, timeline_events)


def founder_hash(founder_ontology: dict[str, Any]) -> str:
    canonical = json.dumps(founder_ontology, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
