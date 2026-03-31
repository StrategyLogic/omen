from __future__ import annotations

from ._schema_utils import validate_with_contract


def test_strategy_ontology_output_contract_accepts_minimal_valid_payload() -> None:
    payload = {
        "meta": {
            "version": "0.1.0",
            "case_id": "xd",
            "domain": "startup_replay",
            "strategy": "evidence-first",
        },
        "tbox": {
            "concepts": [
                {"name": "Actor", "category": "actor"},
                {"name": "StrategicActor", "category": "actor"},
            ],
            "relations": [{"name": "influences"}],
            "axioms": [{"name": "transitivity"}],
        },
        "abox": {
            "actors": [
                {
                    "actor_id": "actor.xd",
                    "actor_type": "StrategicActor",
                    "role": "founder",
                    "profile": {"mental_patterns": {}, "strategic_style": {}},
                },
                {
                    "actor_id": "actor.customer",
                    "actor_type": "Actor",
                    "role": "customer",
                },
            ],
            "capabilities": [{"name": "execution_depth", "score": 0.7}],
            "constraints": [{"name": "market_resistance"}],
            "events": [{"id": "event-1", "name": "Launch"}],
        },
        "reasoning_profile": {
            "activation_rules": [{"rule": "r1"}],
            "propagation_rules": [{"rule": "r2"}],
            "counterfactual_rules": [{"rule": "r3"}],
        },
        "tech_space_ontology": {
            "actors": ["actor.xd"],
            "capabilities": [{"name": "data_pipeline"}],
            "axioms": [{"name": "capability_supports_outcome"}],
        },
        "market_space_ontology": {
            "actors": ["customer.segment.a"],
            "axioms": [{"name": "adoption_barrier"}],
            "market_attributes": {"adoption_resistance": 0.6},
        },
        "shared_actors": ["actor.xd"],
        "case_package": {"documents": []},
        "scenario_id": "xd-replay",
        "name": "X-Developer Replay",
        "time_steps": 12,
        "seed": 7,
        "actors": ["actor.xd"],
        "capabilities": [{"name": "execution_depth"}],
    }

    validate_with_contract(payload, "strategy-ontology-output.schema.json")
