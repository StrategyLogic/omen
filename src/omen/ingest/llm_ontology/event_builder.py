"""Build-time timeline event extraction for case replay."""

from __future__ import annotations

import json
from textwrap import dedent
from typing import Any

from omen.ingest.llm_ontology.clients import create_chat_client
from omen.models.case_replay_models import CaseDocument, LLMConfig


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response does not contain a JSON array")
    payload = json.loads(text[start : end + 1])
    if not isinstance(payload, list):
        raise ValueError("event payload is not a JSON array")
    return [item for item in payload if isinstance(item, dict)]


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


def _normalize_events(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for idx, event in enumerate(items, start=1):
        event_id = str(event.get("id") or f"event.{idx}").strip() or f"event.{idx}"
        time_value = str(event.get("time") or "unknown").strip() or "unknown"
        raw_event = str(event.get("event") or "").strip()
        description = str(event.get("description") or raw_event).strip()
        event_type = str(event.get("event") or event.get("type") or "").strip().lower()
        if not event_type:
            event_type = _classify_event_type(description or raw_event)
        normalized.append(
            {
                "id": event_id,
                "time": time_value,
                "event": event_type,
                "description": description,
                "evidence_refs": event.get("evidence_refs") if isinstance(event.get("evidence_refs"), list) else [],
                "confidence": float(event.get("confidence") or 0.5),
                "is_strategy_related": bool(event.get("is_strategy_related", True)),
            }
        )
    return normalized


def _fallback_events(chunks: list[str]) -> list[dict[str, Any]]:
    raw_events: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks[:5], start=1):
        raw_events.append(
            {
                "id": f"event.{idx}",
                "time": "unknown",
                "description": chunk[:120].strip().replace("\n", " "),
                "evidence_refs": [f"chunk:{idx}"],
                "confidence": 0.4,
                "is_strategy_related": True,
            }
        )
    return _normalize_events(raw_events)


def extract_timeline_events(
    *,
    case_doc: CaseDocument,
    chunks: list[str],
    config: LLMConfig,
) -> list[dict[str, Any]]:
    if not chunks:
        return []

    excerpt = "\n\n---\n\n".join(chunks[: min(len(chunks), config.max_chunks)])
    prompt = dedent(
        f"""
        You are an ontology extraction assistant.
        Extract timeline events from the case document as JSON array only.

        Required item fields:
        - id (string)
        - time (string, e.g. 2016 or 2016-06)
        - event (string enum type only, short token: launch|release|pilot|pricing|expansion|other)
        - description (string, concrete event narrative)
        - evidence_refs (string array)
        - confidence (number in [0,1])
        - is_strategy_related (boolean)

        Rules:
        - Do NOT emit phase/stage fields.
        - Keep only historically grounded events with evidence.
        - Output JSON array only, no markdown.

        Case ID: {case_doc.case_id}
        Title: {case_doc.title}
        Known outcome: {case_doc.known_outcome}

        Content:
        {excerpt}
        """
    ).strip()

    try:
        chat = create_chat_client(config)
        response = chat.invoke(prompt)
        content = response.content if isinstance(response.content, str) else json.dumps(response.content)
        events = _normalize_events(_extract_json_array(content))
        if events:
            return events
    except Exception:
        pass

    return _fallback_events(chunks)
