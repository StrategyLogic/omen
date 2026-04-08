"""Reusable actor artifact pipeline for CLI orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from omen.ingest.synthesizer.assembler import attach_actor_ref, attach_timeline_events
from omen.ingest.synthesizer.services.actor import generate_actor_and_events_from_document
from omen.ingest.synthesizer.services.strategy import generate_strategy_ontology_from_document
from omen.scenario.case_replay_loader import save_strategy_ontology
from omen.ui.artifacts import ACTOR_ONTOLOGY_FILENAME, STRATEGY_ONTOLOGY_FILENAME, ensure_actor_output_dir
from omen.ui.case_catalog import case_display_title, normalize_case_id, suggest_known_outcome


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
