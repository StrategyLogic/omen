"""LLM orchestration for generating Strategy Ontology JSON."""

from __future__ import annotations

import json
from typing import Any

from omen.ingest.llm_ontology.clients import create_chat_client, embed_documents_with_voyage
from omen.ingest.llm_ontology.prompts import (
    build_json_retry_prompt,
    build_system_prompt,
    build_user_prompt,
)
from omen.ingest.llm_ontology.vector_cache import get_cached_vectors, save_vectors_to_cache
from omen.models.case_replay_models import CaseDocument, LLMConfig


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


def _select_chunks_with_embeddings(chunks: list[str], config: LLMConfig) -> list[str]:
    if not chunks:
        return []

    # Try local cache first
    embeddings = get_cached_vectors(chunks, config)

    if embeddings is None:
        try:
            embeddings = embed_documents_with_voyage(config, chunks)
            if embeddings:
                save_vectors_to_cache(chunks, embeddings, config)
        except Exception:
            return chunks[: config.max_chunks]

    if not embeddings:
        return chunks[: config.max_chunks]

    scored: list[tuple[float, str]] = []
    for vector, chunk in zip(embeddings, chunks, strict=False):
        magnitude = sum(abs(v) for v in vector)
        scored.append((magnitude, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[: config.max_chunks]]


def generate_ontology_payload(
    *,
    case_doc: CaseDocument,
    chunks: list[str],
    config: LLMConfig,
    strategy: str | None = None,
    use_embeddings: bool = True,
) -> dict[str, Any]:
    selected_chunks = _select_chunks_with_embeddings(chunks, config) if use_embeddings else chunks[: config.max_chunks]
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
