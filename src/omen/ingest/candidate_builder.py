"""Candidate generation from cleaned text for ontology ingest dry-runs."""

from __future__ import annotations

from typing import Any

from omen.ingest.candidate_mapper import map_candidate_to_concept
from omen.ingest.text_processing import clean_text, split_into_chunks


def build_candidates_from_text(
    text: str,
    *,
    document_id: str,
    concept_names: list[str],
    chunk_size: int = 400,
    chunk_overlap: int = 40,
) -> list[dict[str, Any]]:
    cleaned = clean_text(text)
    chunks = split_into_chunks(cleaned, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    candidates: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        status, concept = map_candidate_to_concept(chunk, concept_names)
        candidates.append(
            {
                "candidate_id": f"{document_id}-{index}",
                "document_id": document_id,
                "entity_text": chunk[:200],
                "entity_type": "strategic_signal",
                "confidence": 0.75 if status == "mapped" else 0.4,
                "evidence_span": {
                    "page": 1,
                    "start": 0,
                    "end": len(chunk),
                },
                "mapping_status": status,
                "proposed_concept_id": concept,
            }
        )
    return candidates
