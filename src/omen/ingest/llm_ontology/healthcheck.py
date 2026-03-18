"""Connectivity healthcheck for Spec 6 LLM dependencies."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from omen.ingest.llm_ontology.clients import create_chat_client, embed_documents_with_voyage
from omen.ingest.llm_ontology.config import load_llm_config

LogFn = Callable[[str, str, str], None]


def _append_step(steps: list[dict[str, Any]], name: str, status: str, detail: str) -> None:
    steps.append(
        {
            "name": name,
            "status": status,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


def run_llm_healthcheck(
    *,
    config_path: str,
    sample_text: str,
    logger: LogFn | None = None,
) -> dict[str, Any]:
    def emit(step: str, status: str, message: str) -> None:
        if logger:
            logger(step, status, message)

    steps: list[dict[str, Any]] = []

    emit("config", "STARTED", f"loading config from {config_path}")
    try:
        config = load_llm_config(config_path)
        detail = (
            f"provider={config.provider}, chat_model={config.chat_model}, "
            f"embedding_model={config.embedding_model}"
        )
        emit("config", "PASSED", detail)
        _append_step(steps, "config", "passed", detail)
    except Exception as exc:
        message = f"failed to load config: {exc}"
        emit("config", "FAILED", message)
        _append_step(steps, "config", "failed", message)
        return {"ok": False, "steps": steps}

    emit("deepseek_chat", "STARTED", "creating chat client")
    try:
        chat = create_chat_client(config)
        emit("deepseek_chat", "RUNNING", "invoking connectivity probe prompt")
        response = chat.invoke(
            "Return exactly one line: Omen-DeepSeek-OK. No extra words."
        )
        content = response.content if isinstance(response.content, str) else str(response.content)
        snippet = content.strip().replace("\n", " ")[:120]
        detail = f"response_preview={snippet}"
        emit("deepseek_chat", "PASSED", detail)
        _append_step(steps, "deepseek_chat", "passed", detail)
    except Exception as exc:
        message = f"chat probe failed: {exc}"
        emit("deepseek_chat", "FAILED", message)
        _append_step(steps, "deepseek_chat", "failed", message)

    emit("voyage_embed", "STARTED", "creating voyage embedding probe")
    try:
        texts = [sample_text, "omen strategic simulation connectivity check"]
        emit("voyage_embed", "RUNNING", f"embedding {len(texts)} texts")
        embeddings = embed_documents_with_voyage(config, texts)
        if not embeddings:
            raise ValueError("empty embeddings returned")
        dims = len(embeddings[0]) if embeddings[0] else 0
        detail = f"vectors={len(embeddings)}, dimensions={dims}"
        emit("voyage_embed", "PASSED", detail)
        _append_step(steps, "voyage_embed", "passed", detail)
    except Exception as exc:
        message = f"embedding probe failed: {exc}"
        emit("voyage_embed", "FAILED", message)
        _append_step(steps, "voyage_embed", "failed", message)

    ok = all(step["status"] == "passed" for step in steps)
    summary = "all probes passed" if ok else "one or more probes failed"
    emit("summary", "DONE", summary)

    return {
        "ok": ok,
        "summary": summary,
        "steps": steps,
        "config": {
            "provider": config.provider,
            "chat_model": config.chat_model,
            "embedding_model": config.embedding_model,
            "timeout_seconds": config.timeout_seconds,
        },
    }
