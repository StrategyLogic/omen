from __future__ import annotations

from ._schema_utils import validate_with_contract


def test_analyze_formation_contract_accepts_chain_payload() -> None:
    payload = {
        "query": {
            "type": "formation",
            "target_event_id": "event-2",
        },
        "formation_chain": {
            "perception": [
                {
                    "source": "market.signal",
                    "source_name": "Market signal",
                    "relation": "indicates",
                    "description": "Customers resisted migration costs.",
                }
            ],
            "constraint_conflict": {
                "internal_constraints": ["limited sales capacity"],
                "external_pressures": [
                    {
                        "source": "competitor.price",
                        "source_name": "Competitor pricing",
                        "relation": "compresses",
                        "description": "Price pressure increased switching hesitation.",
                    }
                ],
            },
            "mediation": {
                "core_beliefs": ["Evidence over rhetoric"],
                "cognitive_frames": ["adoption before scale"],
                "decision_style": "pragmatic",
                "non_negotiables": ["retain product clarity"],
            },
            "decision_logic": {
                "event_id": "event-2",
                "event_name": "Pilot",
                "description": "Pilot selected to reduce perceived adoption risk.",
                "narrative": "Founder traded speed for trust-building evidence.",
            },
            "execution_delta": [
                {
                    "target": "customer.segment.a",
                    "target_name": "Early adopters",
                    "relation": "requires",
                    "description": "Needed onboarding support before expansion.",
                }
            ],
        },
        "evidence_refs": ["event-2", "event-3"],
        "summary": {
            "founder": "Founder X",
            "perception_signal_count": 1,
            "internal_constraint_count": 1,
            "external_pressure_count": 1,
            "execution_delta_count": 1,
        },
    }

    validate_with_contract(payload, "analyze-formation.schema.json")
