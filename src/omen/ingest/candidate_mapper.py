"""Map extracted entity candidates to ontology concept names."""

from __future__ import annotations


def map_candidate_to_concept(entity_text: str, concept_names: list[str]) -> tuple[str, str | None]:
    text = entity_text.lower()
    normalized = {concept.lower(): concept for concept in concept_names}

    matches = [concept for concept_lc, concept in normalized.items() if concept_lc and concept_lc in text]
    if len(matches) > 1:
        return "conflict", None
    if len(matches) == 1:
        return "mapped", matches[0]

    return "unmapped", None
