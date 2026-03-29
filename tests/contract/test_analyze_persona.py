from __future__ import annotations

from ._schema_utils import validate_with_contract


def test_analyze_persona_contract_accepts_request_response_envelope() -> None:
    payload = {
        "request": {
            "case_id": "xd",
            "query_type": "persona",
            "year_range": "2014:2018",
            "prompt_version": "base.persona_insight@1.0.0",
            "evidence_bundle": ["event-1", "event-2"],
        },
        "response": {
            "case_id": "xd",
            "persona": {
                "strategic_intent": "Build compounding semantic leverage",
                "execution_style": "evidence-first iterations",
                "pivot_history": ["analytics-first", "workflow-first"],
            },
            "intent_action_consistency": 0.82,
            "explanation": "Choices stayed consistent with evidence-driven priorities.",
            "evidence_refs": ["event-1", "event-2"],
            "prompt_version": "base.persona_insight@1.0.0",
            "run_meta": {
                "request_id": "req-001",
                "latency_ms": 321,
                "model": "deepseek-chat",
                "generated_at": "2026-03-22T10:20:30Z",
            },
        },
    }

    validate_with_contract(payload, "analyze-persona.schema.json")
