"""Local vector caching for Strategy Ontology generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from omen.models.case_models import LLMConfig


def _get_cache_dir() -> Path:
    cache_dir = Path.home() / ".cache" / "omen" / "vectors"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _compute_content_hash(texts: list[str], model: str) -> str:
    combined = "\n---\n".join(texts)
    key = f"{model}:{combined}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def get_cached_vectors(texts: list[str], config: LLMConfig) -> list[list[float]] | None:
    content_hash = _compute_content_hash(texts, config.embedding_model)
    cache_file = _get_cache_dir() / f"{content_hash}.json"

    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_vectors_to_cache(texts: list[str], vectors: list[list[float]], config: LLMConfig) -> None:
    content_hash = _compute_content_hash(texts, config.embedding_model)
    cache_file = _get_cache_dir() / f"{content_hash}.json"

    try:
        cache_file.write_text(json.dumps(vectors), encoding="utf-8")
    except Exception:
        pass
