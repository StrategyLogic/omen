"""Validation entrypoints for Spec 4 ingest/precision payloads."""

from __future__ import annotations

from omen.ingest.models import (
    ExtractedEntityCandidate,
    OntologyAssertionCandidate,
    PrecisionEvaluationProfile,
)


def validate_precision_profile_or_raise(payload: dict) -> PrecisionEvaluationProfile:
    return PrecisionEvaluationProfile.model_validate(payload)


def validate_extracted_entity_candidate_or_raise(payload: dict) -> ExtractedEntityCandidate:
    return ExtractedEntityCandidate.model_validate(payload)


def validate_extracted_entity_candidates_or_raise(
    payloads: list[dict],
) -> list[ExtractedEntityCandidate]:
    validated: list[ExtractedEntityCandidate] = []
    for payload in payloads:
        validated.append(validate_extracted_entity_candidate_or_raise(payload))
    return validated


def validate_ontology_assertion_candidate_or_raise(payload: dict) -> OntologyAssertionCandidate:
    return OntologyAssertionCandidate.model_validate(payload)


def validate_ontology_assertion_candidates_or_raise(
    payloads: list[dict],
) -> list[OntologyAssertionCandidate]:
    validated: list[OntologyAssertionCandidate] = []
    for payload in payloads:
        validated.append(validate_ontology_assertion_candidate_or_raise(payload))
    return validated
