"""LangChain client factories for DeepSeek + Voyage."""

from __future__ import annotations

import importlib
from typing import Any

from omen.models.case_models import LLMConfig


def create_chat_client(config: LLMConfig) -> Any:
    langchain_openai = importlib.import_module("langchain_openai")
    chat_open_ai = getattr(langchain_openai, "ChatOpenAI")

    return chat_open_ai(
        model=config.chat_model,
        api_key=config.deepseek_api_key,
        base_url=config.base_url,
        timeout=config.timeout_seconds,
        temperature=config.temperature,
    )


def create_voyage_client(config: LLMConfig) -> Any:
    voyageai_module = importlib.import_module("voyageai")
    voyage_client = getattr(voyageai_module, "Client")

    return voyage_client(api_key=config.voyage_api_key)


def embed_documents_with_voyage(config: LLMConfig, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    client = create_voyage_client(config)
    response = client.embed(
        texts=texts,
        model=config.embedding_model,
        input_type="document",
    )

    embeddings = getattr(response, "embeddings", None)
    if embeddings is None:
        return []
    return embeddings
