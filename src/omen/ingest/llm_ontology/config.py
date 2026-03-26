"""Configuration loader for Spec 6 LLM ingestion."""

from __future__ import annotations

import os
import re
import tomllib
import importlib
from pathlib import Path

from omen.models.case_replay_models import LLMConfig

_ENV_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")


def _resolve_env_placeholder(value: str) -> str:
    match = _ENV_PATTERN.match(value.strip())
    if not match:
        return value
    env_key = match.group(1)
    resolved = os.getenv(env_key)
    if not resolved:
        raise ValueError(f"missing env var referenced in config: {env_key}")
    return resolved


def _resolve_optional_env_placeholder(value: str) -> str:
    if not value.strip():
        return ""
    try:
        return _resolve_env_placeholder(value)
    except ValueError:
        return ""


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _load_llm_config_from_env(*, require_embeddings: bool = True) -> LLMConfig:
    deepseek_api_key = str(os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not deepseek_api_key:
        raise FileNotFoundError(
            "LLM config file not found and DEEPSEEK_API_KEY is missing. "
            "Set DEEPSEEK_API_KEY in deployment environment or provide config/llm.toml."
        )

    voyage_api_key = str(os.getenv("VOYAGE_API_KEY") or "").strip()
    if require_embeddings and not voyage_api_key:
        raise FileNotFoundError(
            "LLM config file not found and VOYAGE_API_KEY is missing (required for embeddings). "
            "Set VOYAGE_API_KEY in deployment environment or provide config/llm.toml."
        )

    if not voyage_api_key:
        voyage_api_key = "chat-only"

    return LLMConfig(
        provider="deepseek",
        base_url=str(os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"),
        chat_model=str(os.getenv("DEEPSEEK_CHAT_MODEL") or "deepseek-chat"),
        embedding_model=str(os.getenv("VOYAGE_EMBEDDING_MODEL") or "voyage-3.5"),
        deepseek_api_key=deepseek_api_key,
        voyage_api_key=voyage_api_key,
        timeout_seconds=_env_int("LLM_TIMEOUT_SECONDS", 120),
        temperature=_env_float("LLM_TEMPERATURE", 0.1),
        max_chunks=_env_int("LLM_MAX_CHUNKS", 12),
        chunk_size=_env_int("LLM_CHUNK_SIZE", 1800),
        chunk_overlap=_env_int("LLM_CHUNK_OVERLAP", 200),
    )


def load_llm_config(config_path: str | Path = "config/llm.toml", *, require_embeddings: bool = True) -> LLMConfig:
    try:
        dotenv_module = importlib.import_module("dotenv")
        dotenv_module.load_dotenv(override=False)
    except Exception:
        pass
    path = Path(config_path)
    if not path.exists():
        return _load_llm_config_from_env(require_embeddings=require_embeddings)

    payload = tomllib.loads(path.read_text(encoding="utf-8"))

    provider = payload.get("provider", {})
    auth = payload.get("auth", {})
    runtime = payload.get("runtime", {})

    deepseek_api_key = _resolve_env_placeholder(str(auth.get("deepseek_api_key", "")))
    if require_embeddings:
        voyage_api_key = _resolve_env_placeholder(str(auth.get("voyage_api_key", "")))
    else:
        voyage_api_key = _resolve_optional_env_placeholder(str(auth.get("voyage_api_key", ""))) or "chat-only"

    return LLMConfig(
        provider="deepseek",
        base_url=str(provider.get("base_url", "https://api.deepseek.com")),
        chat_model=str(provider.get("chat_model", "deepseek-chat")),
        embedding_model=str(provider.get("embedding_model", "voyage-3.5")),
        deepseek_api_key=deepseek_api_key,
        voyage_api_key=voyage_api_key,
        timeout_seconds=int(runtime.get("timeout_seconds", 120)),
        temperature=float(runtime.get("temperature", 0.1)),
        max_chunks=int(runtime.get("max_chunks", 12)),
        chunk_size=int(runtime.get("chunk_size", 1800)),
        chunk_overlap=int(runtime.get("chunk_overlap", 200)),
    )
