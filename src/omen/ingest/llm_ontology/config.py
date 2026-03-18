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


def load_llm_config(config_path: str | Path = "config/llm.toml") -> LLMConfig:
    try:
        dotenv_module = importlib.import_module("dotenv")
        dotenv_module.load_dotenv(override=False)
    except Exception:
        pass
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"LLM config not found at {path}. Copy config/llm.example.toml to config/llm.toml first."
        )

    payload = tomllib.loads(path.read_text(encoding="utf-8"))

    provider = payload.get("provider", {})
    auth = payload.get("auth", {})
    runtime = payload.get("runtime", {})

    deepseek_api_key = _resolve_env_placeholder(str(auth.get("deepseek_api_key", "")))
    voyage_api_key = _resolve_env_placeholder(str(auth.get("voyage_api_key", "")))

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
