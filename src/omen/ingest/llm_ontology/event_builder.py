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


def _fallback_events(chunks: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks[:5], start=1):
        events.append(
            {
                "id": f"event.{idx}",
                "time": "unknown",
                "event": chunk[:120].strip().replace("\n", " "),
                "evidence_refs": [f"chunk:{idx}"],
                "confidence": 0.4,
                "is_strategy_related": True,
            }
        )
    return events


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
        - event (string)
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
        events = _extract_json_array(content)
        if events:
            return events
    except Exception:
        pass

    return _fallback_events(chunks)
