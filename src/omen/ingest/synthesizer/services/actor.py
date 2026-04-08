"""Actor and event extraction service."""

from __future__ import annotations

import json
from typing import Callable

from omen.ingest.synthesizer.clients import invoke_text_prompt, render_prompt_template
from omen.ingest.synthesizer.prompts import build_json_retry_prompt
from omen.ingest.synthesizer.prompts.registry import get_prompt_template
from omen.ingest.synthesizer.builders.actor import apply_enhanced_strategic_style
from omen.ingest.synthesizer.builders.actor import extract_strategic_actor_identity
from omen.ingest.synthesizer.builders.actor import is_strategic_style_admissible
from omen.ingest.synthesizer.builders.actor import load_actor_ontology_payload
from omen.ingest.synthesizer.builders.actor import write_actor_ontology_payload
from omen.ingest.synthesizer.config import load_llm_config
from omen.ingest.processor import chunk_case_document, load_case_document
from omen.ingest.synthesizer.builders.event import extract_timeline_events
from omen.ingest.synthesizer.builders.actor import extract_actor_ontology

LogFn = Callable[[str, str, str], None]


def _render_base_prompt(template_key: str, values: dict[str, object]) -> str:
    return render_prompt_template(get_prompt_template(template_key, tier="base"), values)


def _extract_json_object(text: str) -> dict[str, object]:
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM response does not contain JSON object")
    payload, _ = decoder.raw_decode(text[start:])
    if not isinstance(payload, dict):
        raise ValueError("LLM response payload is not an object")
    return payload


def _invoke_json(prompt: str, *, config_path: str, stage: str) -> dict[str, object]:
    content = invoke_text_prompt(config_path=config_path, user_prompt=prompt)
    try:
        return _extract_json_object(content)
    except Exception:
        retry_prompt = build_json_retry_prompt(prompt)
        retry_content = invoke_text_prompt(config_path=config_path, user_prompt=retry_prompt)
        return _extract_json_object(retry_content)


def ensure_strategic_actor_style(
    *,
    actor_ref: str,
    current_case_id_to_exclude: str,
    config_path: str,
) -> dict[str, object]:
    payload = load_actor_ontology_payload(actor_ref)
    trace: dict[str, object] = {
        "stage": "scenario_enhance_prompt",
        "actor_ref": actor_ref,
        "admissible_before": is_strategic_style_admissible(payload),
        "enhanced": False,
        "status": "noop",
        "reason": "",
    }

    if bool(trace["admissible_before"]):
        trace["reason"] = "strategic actor already admissible"
        return trace

    strategic_actor_name, strategic_actor_role = extract_strategic_actor_identity(payload)
    prompt = _render_base_prompt(
        "scenario_enhance_prompt",
        {
            "actor_ref": actor_ref,
            "strategic_actor_name": strategic_actor_name,
            "strategic_actor_role": strategic_actor_role,
            "current_case_id_to_exclude": current_case_id_to_exclude,
            "actor_ontology_json": json.dumps(payload, ensure_ascii=False),
        },
    )
    enhanced = _invoke_json(prompt, config_path=config_path, stage="scenario_enhance_prompt")
    changed = apply_enhanced_strategic_style(payload, enhanced)
    if not changed:
        raise ValueError("scenario_enhance_prompt returned no applicable strategic_style changes")

    write_actor_ontology_payload(actor_ref, payload)
    trace["enhanced"] = True
    trace["status"] = "updated"
    trace["reason"] = "strategic_style enhanced and persisted"
    return trace


def generate_actor_and_events_from_document(
    *,
    document_path: str,
    case_id: str,
    title: str,
    known_outcome: str,
    config_path: str = "config/llm.toml",
    logger: LogFn | None = None,
) -> tuple[dict, list[dict]]:
    def emit(step: str, status: str, message: str) -> None:
        if logger:
            logger(step, status, message)

    emit("actor_config", "STARTED", f"loading llm config from {config_path}")
    llm_config = load_llm_config(config_path)
    emit(
        "actor_config",
        "PASSED",
        f"provider={llm_config.provider}, chat_model={llm_config.chat_model}",
    )

    emit("actor_document", "STARTED", f"loading case document from {document_path}")
    case_doc = load_case_document(
        document_path,
        case_id=case_id,
        title=title,
        known_outcome=known_outcome,
    )
    emit(
        "actor_document",
        "PASSED",
        f"content_type={case_doc.content_type}, chars={len(case_doc.raw_text)}",
    )

    emit("actor_chunking", "RUNNING", "splitting document into chunks")
    chunks = chunk_case_document(
        case_doc,
        chunk_size=llm_config.chunk_size,
        chunk_overlap=llm_config.chunk_overlap,
    )
    emit("actor_chunking", "PASSED", f"chunks={len(chunks)}")

    emit("event_extract", "RUNNING", "extracting timeline events")
    timeline_events = extract_timeline_events(case_doc=case_doc, chunks=chunks, config=llm_config)
    emit("event_extract", "PASSED", f"events={len(timeline_events)}")

    emit("actor_extract", "RUNNING", "extracting actor ontology slice")
    actor_ontology = extract_actor_ontology(
        case_doc=case_doc,
        chunks=chunks,
        config=llm_config,
        timeline_events=timeline_events,
    )
    actor_count = len(actor_ontology.get("actors") or []) if isinstance(actor_ontology, dict) else 0
    emit("actor_extract", "PASSED", f"actors={actor_count}")

    return actor_ontology, timeline_events
