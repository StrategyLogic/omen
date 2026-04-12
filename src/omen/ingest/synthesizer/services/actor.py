"""Actor and event extraction service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

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
PERSONA_INSIGHT_FILENAME = "analyze_persona.json"
STATUS_INSIGHT_FILENAME = "analyze_status.json"


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


def _load_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid json object: {path}")
    return payload


def persona_payload_has_usable_content(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False

    insight = payload.get("persona_insight") if isinstance(payload.get("persona_insight"), dict) else payload
    if not isinstance(insight, dict):
        return False

    narrative = str(insight.get("narrative") or "").strip()
    if narrative:
        return True

    key_traits = insight.get("key_traits")
    if isinstance(key_traits, list):
        for item in key_traits:
            if not isinstance(item, dict):
                continue
            trait = str(item.get("trait") or item.get("name") or "").strip()
            evidence = str(item.get("evidence_summary") or item.get("evidence") or "").strip()
            if trait and evidence:
                return True
    return False


def load_persona_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def status_payload_has_usable_content(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False

    timeline = payload.get("timeline")
    if isinstance(timeline, list) and len(timeline) > 0:
        return True

    summary = payload.get("summary")
    return isinstance(summary, dict) and bool(summary)


def load_status_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def generate_persona_artifact(
    *,
    case_id: str,
    case_dir: Path,
    strategy_payload: dict[str, Any] | None,
    actor_payload: dict[str, Any],
    config_path: str,
    output_path: str | Path | None = None,
) -> Path:
    from omen.analysis.actor.insight import generate_and_save_persona_insight
    from omen.ingest.synthesizer.prompts.registry import ensure_analyze_prompt_available

    ensure_analyze_prompt_available("persona")
    target_path = Path(output_path) if output_path else case_dir / PERSONA_INSIGHT_FILENAME

    return generate_and_save_persona_insight(
        case_id=case_id,
        actor_ontology=actor_payload,
        strategy_ontology=strategy_payload,
        config_path=config_path,
        output_path=target_path,
    )


def ensure_persona_artifact_if_missing(
    *,
    case_id: str,
    case_dir: Path,
    config_path: str,
) -> Path:
    persona_path = case_dir / PERSONA_INSIGHT_FILENAME

    existing_payload = load_persona_payload(persona_path)
    if persona_payload_has_usable_content(existing_payload):
        return persona_path
    if persona_path.exists():
        print(f"Persona insight exists but is empty/unusable, regenerating: {persona_path}")

    strategy_path = case_dir / STRATEGY_ONTOLOGY_FILENAME
    actor_path = case_dir / ACTOR_ONTOLOGY_FILENAME
    if not actor_path.exists():
        raise FileNotFoundError(f"missing actor artifact: {actor_path}")

    actor_payload = _load_json_dict(actor_path)
    strategy_payload = _load_json_dict(strategy_path) if strategy_path.exists() else None
    if strategy_payload is None:
        raise FileNotFoundError(f"missing strategy artifact: {strategy_path}")

    return generate_persona_artifact(
        case_id=case_id,
        case_dir=case_dir,
        strategy_payload=strategy_payload,
        actor_payload=actor_payload,
        config_path=config_path,
        output_path=persona_path,
    )


def ensure_persona_artifact_for_actor_ref(
    *,
    actor_ref: str,
    config_path: str,
) -> Path | None:
    raw = str(actor_ref or "").strip()
    if not raw:
        return None

    actor_path = Path(raw)
    if not actor_path.is_absolute():
        actor_path = Path.cwd() / actor_path
    if not actor_path.exists() or actor_path.name != ACTOR_ONTOLOGY_FILENAME:
        return None

    case_dir = actor_path.parent
    case_id = case_dir.name
    return ensure_persona_artifact_if_missing(
        case_id=case_id,
        case_dir=case_dir,
        config_path=config_path,
    )


def generate_status_artifact(
    *,
    case_dir: Path,
    strategy_payload: dict[str, Any],
    actor_payload: dict[str, Any],
    output_path: str | Path | None = None,
) -> Path:
    from omen.analysis.actor.query import build_events_snapshot

    target_path = Path(output_path) if output_path else case_dir / STATUS_INSIGHT_FILENAME
    status_payload = build_events_snapshot(
        strategy_ontology=strategy_payload,
        actor_ontology=actor_payload,
        year=None,
        date=None,
    )
    target_path.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target_path


def ensure_status_artifact_if_missing(
    *,
    case_dir: Path,
) -> Path | None:
    status_path = case_dir / STATUS_INSIGHT_FILENAME

    existing_payload = load_status_payload(status_path)
    if status_payload_has_usable_content(existing_payload):
        return status_path
    if status_path.exists():
        print(f"Status insight exists but is empty/unusable, regenerating: {status_path}")

    strategy_path = case_dir / STRATEGY_ONTOLOGY_FILENAME
    actor_path = case_dir / ACTOR_ONTOLOGY_FILENAME
    if not actor_path.exists():
        return None
    if not strategy_path.exists():
        return None

    actor_payload = _load_json_dict(actor_path)
    strategy_payload = _load_json_dict(strategy_path)
    return generate_status_artifact(
        case_dir=case_dir,
        strategy_payload=strategy_payload,
        actor_payload=actor_payload,
        output_path=status_path,
    )


def ensure_status_artifact_for_actor_ref(
    *,
    actor_ref: str,
) -> Path | None:
    raw = str(actor_ref or "").strip()
    if not raw:
        return None

    actor_path = Path(raw)
    if not actor_path.is_absolute():
        actor_path = Path.cwd() / actor_path
    if not actor_path.exists() or actor_path.name != ACTOR_ONTOLOGY_FILENAME:
        return None

    case_dir = actor_path.parent
    return ensure_status_artifact_if_missing(case_dir=case_dir)


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
