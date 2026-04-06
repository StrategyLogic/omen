from omen.scenario.contract_loader import load
from omen.scenario.ingest_validator import (
    validate_extracted_entity_candidate_or_raise,
    validate_ontology_assertion_candidates_or_raise,
    validate_ontology_assertion_candidate_or_raise,
    validate_precision_profile_or_raise,
)


def test_validate_precision_profile_or_raise() -> None:
    payload = {
        "profile_id": "p-1",
        "case_id": "ontology",
        "repeatability_threshold": 0.9,
        "directional_correctness_threshold": 0.85,
        "trace_completeness_threshold": 0.95,
        "status": "active",
    }
    profile = validate_precision_profile_or_raise(payload)
    assert profile.status == "active"


def test_validate_extracted_entity_candidate_or_raise() -> None:
    payload = {
        "candidate_id": "c-1",
        "document_id": "d-1",
        "entity_text": "semantic retrieval",
        "entity_type": "capability",
        "confidence": 0.88,
        "evidence_span": {"page": 2, "start": 10, "end": 32},
        "mapping_status": "mapped",
        "proposed_concept_id": "SemanticRetrieval",
    }
    candidate = validate_extracted_entity_candidate_or_raise(payload)
    assert candidate.mapping_status == "mapped"


def test_validate_ontology_assertion_candidate_or_raise() -> None:
    payload = {
        "assertion_id": "a-1",
        "subject_concept": "AIMemoryActor",
        "predicate": "has_capability",
        "object_concept": "SemanticRetrieval",
        "source_candidates": ["c-1"],
        "review_state": "pending",
    }
    assertion = validate_ontology_assertion_candidate_or_raise(payload)
    assert assertion.review_state == "pending"


def test_validate_ontology_assertion_candidates_or_raise() -> None:
    payloads = [
        {
            "assertion_id": "a-1",
            "subject_concept": "doc-1",
            "predicate": "mentions_concept",
            "object_concept": "AIMemoryActor",
            "source_candidates": ["c-1"],
            "review_state": "pending",
        },
        {
            "assertion_id": "a-2",
            "subject_concept": "doc-1",
            "predicate": "mentions_concept",
            "object_concept": "UNMAPPED",
            "source_candidates": ["c-2"],
            "review_state": "rejected",
        },
    ]
    assertions = validate_ontology_assertion_candidates_or_raise(payloads)
    assert len(assertions) == 2


def test_load_spec4_contract_schema() -> None:
    schema = load("precision-evaluation.schema.json")
    assert schema["title"] == "PrecisionEvaluationProfile"
