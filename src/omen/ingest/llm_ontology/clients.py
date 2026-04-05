"""LangChain client factories for DeepSeek + Voyage."""

from __future__ import annotations

import importlib
import json
from typing import Any

from omen.ingest.llm_ontology.config import load_llm_config
from omen.ingest.models import LLMConfig


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


def render_prompt_template(template: str, values: dict[str, object]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"[[{key}]]", str(value))
    return rendered.strip()


def invoke_text_prompt(
    *,
    config_path: str,
    user_prompt: str,
    system_prompt: str | None = None,
) -> str:
    config = load_llm_config(config_path)
    chat = create_chat_client(config)
    prompt_parts = [part.strip() for part in (system_prompt or "", user_prompt) if str(part).strip()]
    response = chat.invoke("\n\n".join(prompt_parts))
    content = response.content
    if isinstance(content, str):
        return content.strip()
    return json.dumps(content, ensure_ascii=False).strip()


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
