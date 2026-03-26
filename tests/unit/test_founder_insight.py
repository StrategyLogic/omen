import json

from omen.analysis.founder.insight import generate_unified_insight


class _MockResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _MockChatClient:
    def __init__(self) -> None:
        self._responses = [
            _MockResponse(
                json.dumps(
                    {
                        "narrative": "The founder formed strategy by filtering customer reality through a strong evidence-first operating belief.",
                        "key_traits": [
                            {"trait": "Evidence-First", "evidence_summary": "Repeatedly prioritizes measurable signals."},
                            {"trait": "Principled", "evidence_summary": "Protects non-negotiables under pressure."},
                        ],
                        "consistency_score": 0.91,
                    },
                    ensure_ascii=False,
                )
            ),
            _MockResponse(
                json.dumps(
                    [
                        {
                            "question": "Why did the founder prioritize a data-driven path?",
                            "answer": "Because he considered workflow data more truthful than manual process reporting.",
                            "evidence_refs": ["event-1"],
                        },
                        {
                            "question": "Why were constraints treated as filters?",
                            "answer": "Because constraints helped narrow execution to decisions compatible with strategic identity.",
                            "evidence_refs": ["event-2"],
                        },
                        {
                            "question": "Why did execution still diverge?",
                            "answer": "Because customer adoption introduced non-linear friction that strategy alone could not remove.",
                            "evidence_refs": ["event-3"],
                        },
                    ],
                    ensure_ascii=False,
                )
            ),
            _MockResponse(
                json.dumps(
                    {
                        "process_gaps": [
                            {
                                "assumption": "Process alignment would be fast.",
                                "observation": "Adoption required staged validation.",
                                "gap_significance": "Shows execution friction.",
                                "event_id": "event-1",
                                "phase": "launch",
                            },
                            {
                                "assumption": "Consistency would preserve speed.",
                                "observation": "Execution required adaptation cycles.",
                                "gap_significance": "Shows speed tradeoff.",
                                "event_id": "event-2",
                                "phase": "pilot",
                            },
                            {
                                "assumption": "Value would be self-evident.",
                                "observation": "Trust-building was still necessary.",
                                "gap_significance": "Shows market education burden.",
                                "event_id": "event-3",
                                "phase": "pricing",
                            },
                        ],
                        "outcome_gaps": [
                            {
                                "assumption": "Process success transfers to outcome success.",
                                "observation": "Outcome lagged market expectations.",
                                "gap_significance": "Separates process success from outcome timing.",
                                "event_id": "event-1",
                                "phase": "launch",
                            }
                        ],
                        "learning_loop": [
                            {
                                "signal": "Pilot feedback",
                                "adjustment": "Commercial packaging was refined after validation.",
                                "evidence_ref": "event-2",
                            }
                        ],
                    },
                    ensure_ascii=False,
                )
            ),
        ]

    def invoke(self, prompt: str):
        assert prompt
        return self._responses.pop(0)


def test_generate_unified_insight_uses_llm_outputs_when_client_is_available() -> None:
    founder_ontology = {
        "meta": {"case_id": "x-developer"},
        "actors": [
            {
                "id": "founder-1",
                "type": "founder",
                "name": "Founder X",
                "profile": {
                    "mental_patterns": {"core_beliefs": ["data is truth"]},
                    "strategic_style": {
                        "decision_style": "evidence-based",
                        "non_negotiables": ["no manual reporting"],
                    },
                },
            }
        ],
        "events": [
            {"id": "event-1", "name": "Launch"},
            {"id": "event-2", "name": "Pilot"},
            {"id": "event-3", "name": "Pricing"},
        ],
        "influences": [],
    }
    strategy_ontology = {"meta": {"known_outcome": "Market entry succeeded but adoption stayed gradual."}}
    formation_payload = {"query": {"target_event_id": "event-2"}, "formation_chain": {}, "summary": {"stage": "pilot"}}

    payload = generate_unified_insight(
        case_id="x-developer",
        founder_ontology=founder_ontology,
        strategy_ontology=strategy_ontology,
        formation_payload=formation_payload,
        llm_client=_MockChatClient(),
    )

    assert payload["run_meta"]["mode"] == "llm-enhanced"
    assert payload["persona_insight"]["consistency_score"] == 0.91
    assert len(payload["why_chain"]) >= 3
    assert len(payload["gap_analysis"]["process_gaps"]) >= 3
    assert payload["gap_analysis"]["learning_loop"][0]["signal"] == "Pilot feedback"