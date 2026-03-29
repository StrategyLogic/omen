"""Actor-service facade for Spec 7 migration.

This keeps the current founder extraction implementation reusable while exposing
an actor-named service API.
"""

from __future__ import annotations

from typing import Any

from omen.ingest.llm_ontology.founder_service import generate_founder_and_events_from_document


def generate_actor_and_events_from_document(
    *,
    document_path: str,
    case_id: str,
    title: str,
    known_outcome: str,
    config_path: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return generate_founder_and_events_from_document(
        document_path=document_path,
        case_id=case_id,
        title=title,
        known_outcome=known_outcome,
        config_path=config_path,
    )
