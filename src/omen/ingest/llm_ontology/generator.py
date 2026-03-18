"""LLM orchestration for generating Strategy Ontology JSON."""

from __future__ import annotations

import json
from typing import Any

from omen.ingest.llm_ontology.clients import create_chat_client, embed_documents_with_voyage
from omen.ingest.llm_ontology.prompts import build_system_prompt, build_user_prompt
from omen.models.case_replay_models import CaseDocument, LLMConfig


def _extract_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response does not contain a JSON object")
    return json.loads(text[start : end + 1])


def _select_chunks_with_embeddings(chunks: list[str], config: LLMConfig) -> list[str]:
    if not chunks:
        return []
    try:
        embeddings = embed_documents_with_voyage(config, chunks)
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
) -> dict[str, Any]:
    selected_chunks = _select_chunks_with_embeddings(chunks, config)
    chat = create_chat_client(config)
    prompt = f"{build_system_prompt()}\n\n{build_user_prompt(case_doc, selected_chunks, strategy=strategy)}"
    response = chat.invoke(prompt)
    content = response.content if isinstance(response.content, str) else json.dumps(response.content)
    return _extract_json_object(content)
