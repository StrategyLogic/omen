"""Build ontology assertion candidates from extracted entity candidates."""

from __future__ import annotations

from typing import Any


def _decide_review_state(
    mapping_status: str,
    confidence: float,
    *,
    auto_approve_mapped: bool,
    auto_approve_threshold: float,
) -> tuple[str, str | None]:
    if mapping_status == "conflict":
        return "rejected", "conflicting concept matches; requires manual resolution"
    if mapping_status == "unmapped":
        return "rejected", "no ontology concept mapping; requires manual review"

    if auto_approve_mapped and confidence >= auto_approve_threshold:
        return "approved", "auto-approved: mapped with high confidence"

    return "pending", "mapped candidate pending domain review"


def build_assertions_from_candidates(
    candidates: list[dict[str, Any]],
    *,
    auto_approve_mapped: bool = False,
    auto_approve_threshold: float = 0.9,
) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []

    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id"))
        document_id = str(candidate.get("document_id"))
        mapping_status = str(candidate.get("mapping_status", "unmapped"))
        confidence = float(candidate.get("confidence", 0.0))
        proposed_concept = candidate.get("proposed_concept_id")

        review_state, review_notes = _decide_review_state(
            mapping_status,
            confidence,
            auto_approve_mapped=auto_approve_mapped,
            auto_approve_threshold=auto_approve_threshold,
        )

        object_concept = str(proposed_concept) if proposed_concept else "UNMAPPED"
        assertions.append(
            {
                "assertion_id": f"assert-{candidate_id}",
                "subject_concept": document_id,
                "predicate": "mentions_concept",
                "object_concept": object_concept,
                "source_candidates": [candidate_id],
                "review_state": review_state,
                "review_notes": review_notes,
            }
        )

    return assertions
