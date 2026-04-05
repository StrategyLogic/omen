"""Validation entrypoints for Spec 4 ingest/precision payloads."""

from __future__ import annotations

from omen.ingest.models import (
    ExtractedEntityCandidate,
    OntologyAssertionCandidate,
    PrecisionEvaluationProfile,
)


class ScenarioCompilationError(ValueError):
    """Base error for scenario compilation validation failures."""


class AmbiguousScenarioDescriptionError(ScenarioCompilationError):
    """Raised when NL scenario description cannot be deterministically compiled."""


class IncompleteDeterministicPackError(ScenarioCompilationError):
    """Raised when compiled deterministic pack misses required scenario slots."""


class DeferredScopeFeatureError(ScenarioCompilationError):
    """Raised when request includes capabilities deferred out of current release scope."""


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
