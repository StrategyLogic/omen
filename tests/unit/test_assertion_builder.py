from omen.ingest.llm_ontology.builders.assertion import build_assertions_from_candidates


def test_assertion_builder_rejects_unmapped_or_conflict() -> None:
    candidates = [
        {
            "candidate_id": "c1",
            "document_id": "doc1",
            "mapping_status": "unmapped",
            "confidence": 0.8,
            "proposed_concept_id": None,
        },
        {
            "candidate_id": "c2",
            "document_id": "doc1",
            "mapping_status": "conflict",
            "confidence": 0.95,
            "proposed_concept_id": None,
        },
    ]

    assertions = build_assertions_from_candidates(candidates)

    assert assertions[0]["review_state"] == "rejected"
    assert assertions[1]["review_state"] == "rejected"


def test_assertion_builder_auto_approves_only_high_conf_mapped() -> None:
    candidates = [
        {
            "candidate_id": "c1",
            "document_id": "doc1",
            "mapping_status": "mapped",
            "confidence": 0.92,
            "proposed_concept_id": "AIMemoryActor",
        },
        {
            "candidate_id": "c2",
            "document_id": "doc1",
            "mapping_status": "mapped",
            "confidence": 0.7,
            "proposed_concept_id": "DatabaseActor",
        },
    ]

    assertions = build_assertions_from_candidates(
        candidates,
        auto_approve_mapped=True,
        auto_approve_threshold=0.9,
    )

    assert assertions[0]["review_state"] == "approved"
    assert assertions[1]["review_state"] == "pending"
