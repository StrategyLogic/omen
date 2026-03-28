"""YAML-backed prompt template loader."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def get_prompt_config_dir() -> Path:
    return get_repo_root() / "config" / "prompts"


def get_prompt_file_path(tier: str) -> Path:
    normalized_tier = str(tier).strip().lower()
    return get_prompt_config_dir() / f"prompts_{normalized_tier}.yaml"


@lru_cache(maxsize=8)
def load_prompt_file(path: str | Path) -> dict[str, str]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"prompt file not found: {file_path}")

    payload = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"prompt file must decode to an object: {file_path}")

    prompts = payload.get("prompts") or {}
    if not isinstance(prompts, dict):
        raise ValueError(f"prompt file must contain mapping `prompts`: {file_path}")

    normalized: dict[str, str] = {}
    for key, value in prompts.items():
        if not isinstance(key, str) or not key.strip():
            continue
        if not isinstance(value, str):
            raise ValueError(f"prompt `{key}` must be a string in {file_path}")
        normalized[key.strip()] = value.strip()
    return normalized


def load_tier_prompts(tier: str) -> dict[str, str]:
    return load_prompt_file(get_prompt_file_path(tier))


def reset_prompt_loader_cache() -> None:
    load_prompt_file.cache_clear()
