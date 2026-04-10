"""LangChain client factories for DeepSeek + Voyage."""

from __future__ import annotations

import importlib
import json
from typing import Any

from omen.ingest.synthesizer.config import load_llm_config
from omen.ingest.models import LLMConfig
from omen.ingest.synthesizer.services.errors import LLMJsonValidationAbort


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
    config_path: str | None = None,
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


def extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM response does not contain JSON object")
    payload, _ = decoder.raw_decode(text[start:])
    if not isinstance(payload, dict):
        raise ValueError("LLM response payload is not an object")
    return payload


def extract_json_array(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    start = text.find("[")
    if start == -1:
        raise ValueError("LLM response does not contain JSON array")
    payload, _ = decoder.raw_decode(text[start:])
    if not isinstance(payload, list):
        raise ValueError("LLM response payload is not a JSON array")
    return [item for item in payload if isinstance(item, dict)]


def invoke_json_prompt(
    *,
    user_prompt: str,
    system_prompt: str | None = None,
    config_path: str | None = None,
    config: LLMConfig | None = None,
    allow_retry: bool = False,
    retry_prompt: str | None = None,
    stage: str = "llm_json",
    expected_type: str = "object",
) -> dict[str, Any] | list[dict[str, Any]]:
    if config is not None:
        chat = create_chat_client(config)
        prompt_parts = [part.strip() for part in (system_prompt or "", user_prompt) if str(part).strip()]
        response = chat.invoke("\n\n".join(prompt_parts))
        content = response.content
        raw_output = content.strip() if isinstance(content, str) else json.dumps(content, ensure_ascii=False).strip()
    else:
        raw_output = invoke_text_prompt(
            config_path=config_path,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
        )

    parser = extract_json_object if expected_type == "object" else extract_json_array

    try:
        return parser(raw_output)
    except Exception as exc:
        if not allow_retry or not retry_prompt:
            raise LLMJsonValidationAbort(
                stage=stage,
                reason=str(exc),
                raw_output=raw_output,
            ) from exc

    retry_output = invoke_text_prompt(
        config_path=config_path,
        user_prompt=retry_prompt,
        system_prompt=system_prompt,
    )
    try:
        return parser(retry_output)
    except Exception as retry_exc:
        raise LLMJsonValidationAbort(
            stage=stage,
            reason=str(retry_exc),
            raw_output=raw_output,
            retry_output=retry_output,
        ) from retry_exc


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
