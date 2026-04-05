"""LLM orchestration for generating Strategy Ontology JSON."""

from __future__ import annotations

import json
from typing import Any

from omen.ingest.synthesizer.clients import create_chat_client
from omen.ingest.synthesizer.prompts import (
    build_json_retry_prompt,
    build_system_prompt,
    build_user_prompt,
)
from omen.ingest.models import CaseDocument, LLMConfig


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM response does not contain a JSON object")
    candidate = text[start:]
    payload, _ = decoder.raw_decode(candidate)
    if not isinstance(payload, dict):
        raise ValueError("LLM response JSON payload is not an object")
    return payload


def generate_ontology_payload(
    *,
    case_doc: CaseDocument,
    chunks: list[str],
    config: LLMConfig,
    strategy: str | None = None,
) -> dict[str, Any]:
    selected_chunks = chunks[: config.max_chunks]
    chat = create_chat_client(config)
    prompt = f"{build_system_prompt()}\n\n{build_user_prompt(case_doc, selected_chunks, strategy=strategy)}"
    response = chat.invoke(prompt)
    content = response.content if isinstance(response.content, str) else json.dumps(response.content)
    try:
        return _extract_json_object(content)
    except Exception:
        retry_prompt = build_json_retry_prompt(prompt)
        retry_response = chat.invoke(retry_prompt)
        retry_content = (
            retry_response.content
            if isinstance(retry_response.content, str)
            else json.dumps(retry_response.content)
        )
        return _extract_json_object(retry_content)
