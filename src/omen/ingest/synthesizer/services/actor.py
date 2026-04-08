"""Actor and event extraction service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from omen.ingest.synthesizer.assembler import attach_actor_ref, attach_timeline_events
from omen.ingest.synthesizer.config import load_llm_config
from omen.ingest.processor import chunk_case_document, load_case_document
from omen.ingest.synthesizer.builders.event import extract_timeline_events
from omen.ingest.synthesizer.builders.actor import extract_actor_ontology
from omen.ingest.synthesizer.services.strategy import generate_strategy_ontology_from_document
from omen.scenario.case_replay_loader import save_strategy_ontology
from omen.ui.artifacts import ACTOR_ONTOLOGY_FILENAME, STRATEGY_ONTOLOGY_FILENAME, ensure_actor_output_dir
from omen.ui.case_catalog import case_display_title, normalize_case_id, suggest_known_outcome

LogFn = Callable[[str, str, str], None]


def _resolve_doc_path(doc: str) -> Path:
    raw = str(doc).strip()
    if "/" in raw:
        candidate = Path(raw)
        if not candidate.suffix:
            candidate = candidate.with_suffix(".md")
        return candidate

    stem = raw[:-3] if raw.endswith(".md") else raw
    actor_candidate = Path("cases/actors") / f"{stem}.md"
    if actor_candidate.exists():
        return actor_candidate
    return Path("cases") / f"{stem}.md"


def ensure_actor_artifacts(
    *,
    doc: str,
    title: str | None,
    known_outcome: str | None,
    config_path: str,
    output_dir: str,
) -> tuple[str, Path]:
    case_id = normalize_case_id(doc)
    doc_path = _resolve_doc_path(doc)
    if not doc_path.exists():
        raise FileNotFoundError(f"document not found: {doc_path}")

    case_dir = ensure_actor_output_dir(case_id, output_root=output_dir)
    strategy_path = case_dir / STRATEGY_ONTOLOGY_FILENAME
    actor_path = case_dir / ACTOR_ONTOLOGY_FILENAME

    if strategy_path.exists() and actor_path.exists():
        return case_id, case_dir

    effective_title = title or case_display_title(case_id)
    effective_known_outcome = known_outcome or suggest_known_outcome(case_id)

    generation = generate_strategy_ontology_from_document(
        document_path=str(doc_path),
        case_id=case_id,
        title=effective_title,
        strategy=None,
        known_outcome=effective_known_outcome,
        config_path=config_path,
    )
    known_outcome_effective = generation.inferred_known_outcome or effective_known_outcome

    actor_payload, timeline_events = generate_actor_and_events_from_document(
        document_path=str(doc_path),
        case_id=case_id,
        title=effective_title,
        known_outcome=known_outcome_effective,
        config_path=config_path,
    )

    strategy_payload = attach_timeline_events(generation.strategy_ontology, timeline_events)
    strategy_payload = attach_actor_ref(
        strategy_payload,
        actor_payload,
        actor_filename=actor_path.name,
    )

    save_strategy_ontology(strategy_payload, strategy_path)
    actor_path.write_text(json.dumps(actor_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "case_id": case_id,
        "strategy_ontology_path": str(strategy_path),
        "actor_ontology_path": str(actor_path),
        "validation_passed": generation.validation_passed,
        "validation_issues": generation.validation_issues,
        "reused_existing": False,
    }
    (case_dir / "generation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return case_id, case_dir


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
