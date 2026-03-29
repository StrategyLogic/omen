from __future__ import annotations

from ._schema_utils import validate_with_contract


def test_analyze_why_contract_accepts_request_response_envelope() -> None:
    payload = {
        "request": {
            "case_id": "xd",
            "decision_id": "event-2",
            "year": 2017,
        },
        "response": {
            "case_id": "xd",
            "decision_id": "event-2",
            "analysis": {
                "aligned_intent": "Keep adoption friction low",
                "driving_constraints": ["limited enterprise trust"],
                "alternatives_considered": ["heavy governance rollout"],
                "outcome": "selected incremental pilot deployment",
            },
            "evidence_refs": ["event-2", "event-3"],
            "run_meta": {
                "request_id": "req-why-01",
                "generated_at": "2026-03-22T11:00:00Z",
            },
        },
    }

    validate_with_contract(payload, "analyze-why.schema.json")
