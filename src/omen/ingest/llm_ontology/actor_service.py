"""Actor/event slice generation service for build-time pipeline."""

from __future__ import annotations

from typing import Callable

from omen.ingest.llm_ontology.config import load_llm_config
from omen.ingest.llm_ontology.document_loader import chunk_case_document, load_case_document
from omen.ingest.llm_ontology.event_builder import extract_timeline_events
from omen.ingest.llm_ontology.actor_enhancer import enhance_actor_decision_relationships
from omen.ingest.llm_ontology.actor_builder import extract_actor_ontology


LogFn = Callable[[str, str, str], None]


def generate_actor_and_events_from_document(
    *,
    document_path: str,
    case_id: str,
    title: str,
    known_outcome: str,
    config_path: str = "config/llm.toml",
    require_embeddings: bool = True,
    logger: LogFn | None = None,
) -> tuple[dict, list[dict]]:
    def emit(step: str, status: str, message: str) -> None:
        if logger:
            logger(step, status, message)

    emit("actor_config", "STARTED", f"loading llm config from {config_path}")
    llm_config = load_llm_config(config_path, require_embeddings=require_embeddings)
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
    emit("actor_enhance", "RUNNING", "enhancing semantic relations between actors")
    actor_ontology, added_relations = enhance_actor_decision_relationships(
        actor_ontology,
        config=llm_config,
    )
    emit("actor_enhance", "PASSED", f"added_relations={added_relations}")
    actor_count = len(actor_ontology.get("actors") or []) if isinstance(actor_ontology, dict) else 0
    emit("actor_extract", "PASSED", f"actors={actor_count}")

    return actor_ontology, timeline_events
