"""Public service for document-to-ontology generation and validation."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Callable

from omen.ingest.llm_ontology.config import load_llm_config
from omen.ingest.llm_ontology.document_loader import chunk_case_document, load_case_document
from omen.ingest.llm_ontology.generator import generate_ontology_payload
from omen.models.case_replay_models import OntologyGenerationResult
from omen.scenario.ontology_validator import OntologyValidationError, validate_ontology_input_or_raise

LogFn = Callable[[str, str, str], None]


def generate_strategy_ontology_from_document(
    *,
    document_path: str,
    case_id: str,
    title: str,
    known_outcome: str,
    strategy: str | None = None,
    config_path: str = "config/llm.toml",
    require_embeddings: bool = True,
    use_embeddings: bool = True,
    logger: LogFn | None = None,
) -> OntologyGenerationResult:
    def emit(step: str, status: str, message: str) -> None:
        if logger:
            logger(step, status, message)

    emit("config", "STARTED", f"loading llm config from {config_path}")
    llm_config = load_llm_config(config_path, require_embeddings=require_embeddings)
    emit(
        "config",
        "PASSED",
        f"provider={llm_config.provider}, chat_model={llm_config.chat_model}, embedding_model={llm_config.embedding_model}",
    )

    emit("document", "STARTED", f"loading case document from {document_path}")
    case_doc = load_case_document(
        document_path,
        case_id=case_id,
        title=title,
        known_outcome=known_outcome,
    )
    emit("document", "PASSED", f"content_type={case_doc.content_type}, chars={len(case_doc.raw_text)}")

    emit("chunking", "RUNNING", "splitting document into chunks")
    chunks = chunk_case_document(
        case_doc,
        chunk_size=llm_config.chunk_size,
        chunk_overlap=llm_config.chunk_overlap,
    )
    emit("chunking", "PASSED", f"chunks={len(chunks)}")

    emit("ontology_generation", "RUNNING", "calling llm to generate ontology payload")
    payload = generate_ontology_payload(
        case_doc=case_doc,
        chunks=chunks,
        config=llm_config,
        strategy=strategy,
        use_embeddings=use_embeddings,
    )
    inferred_known_outcome = str(payload.pop("known_outcome", "") or "").strip() or None
    payload.setdefault("meta", {})
    if strategy:
        payload["meta"]["strategy"] = strategy
    if inferred_known_outcome:
        payload["meta"]["known_outcome"] = inferred_known_outcome
    emit("ontology_generation", "PASSED", f"top_level_keys={len(payload.keys())}")

    try:
        emit("ontology_validation", "RUNNING", "validating ontology payload")
        validate_ontology_input_or_raise(payload)
        emit("ontology_validation", "PASSED", "ontology payload passed schema+semantic validation")
        return OntologyGenerationResult(
            case_id=case_id,
            strategy_ontology=payload,
            inferred_known_outcome=inferred_known_outcome,
            validation_passed=True,
            validation_issues=[],
            generated_at=datetime.now(),
        )
    except OntologyValidationError as exc:
        issues = [asdict(issue) for issue in exc.issues]
        emit("ontology_validation", "FAILED", f"validation issues={len(issues)}")
        return OntologyGenerationResult(
            case_id=case_id,
            strategy_ontology=payload,
            inferred_known_outcome=inferred_known_outcome,
            validation_passed=False,
            validation_issues=issues,
            generated_at=datetime.now(),
        )
