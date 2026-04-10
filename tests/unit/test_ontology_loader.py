from omen.ingest.synthesizer.builders.scenario import bind_ontology_to_scenario
from omen.ingest.validators.strategy import validate_ontology_input_or_raise
from omen.ingest.validators.scenario import validate_scenario_or_raise


def test_bind_ontology_to_scenario_includes_space_summary() -> None:
    ontology_payload = {
        "meta": {"version": "1.0", "case_id": "demo", "domain": "strategy"},
        "tbox": {
            "concepts": [
                {"name": "StartupActor", "description": "", "category": "actor"},
                {"name": "tech_capability", "description": "", "category": "capability"},
            ],
            "relations": [
                {
                    "name": "has_capability",
                    "source": "StartupActor",
                    "target": "tech_capability",
                    "description": "",
                }
            ],
            "axioms": [{"id": "ax-1", "statement": "sample", "type": "activation"}],
        },
        "abox": {
            "actors": [
                {"actor_id": "startup", "actor_type": "StartupActor"},
                {"actor_id": "market", "actor_type": "StartupActor"},
            ],
            "capabilities": [{"actor_id": "startup", "name": "tech_capability", "score": 0.8}],
            "constraints": [],
        },
        "reasoning_profile": {"activation_rules": [{"rule_id": "ax-1"}]},
        "tech_space_ontology": {
            "actors": [{"actor_id": "startup"}, {"actor_id": "market"}],
            "capabilities": [{"name": "tech_capability", "score": 0.8}],
            "axioms": [{"id": "tax-1", "statement": "tech evolves"}],
        },
        "market_space_ontology": {
            "actors": [{"actor_id": "startup"}],
            "market_attributes": {
                "adoption_resistance": 0.72,
                "incumbent_response_speed": 0.65,
                "value_perception_gap": 0.55,
            },
            "axioms": [{"id": "max-1", "statement": "resistance slows adoption"}],
        },
        "shared_actors": ["startup"],
    }

    scenario_payload = {
        "scenario_id": "demo-scenario",
        "name": "demo",
        "time_steps": 5,
        "seed": 42,
        "user_overlap_threshold": 0.2,
        "actors": [
            {
                "actor_id": "startup",
                "actor_type": "StartupActor",
                "budget": 1000,
                "initial_user_base": 300,
                "available_actions": ["grow_semantic_layer"],
                "functional_profile": {"semantic": 0.8, "consistency": 0.7, "developer_experience": 0.7},
            },
            {
                "actor_id": "market",
                "actor_type": "StartupActor",
                "budget": 900,
                "initial_user_base": 250,
                "available_actions": ["defend_core"],
                "functional_profile": {"semantic": 0.6, "consistency": 0.6, "developer_experience": 0.6},
            },
        ],
        "capabilities": [{"name": "tech_capability", "weight": 1.0}],
    }

    ontology = validate_ontology_input_or_raise(ontology_payload)
    scenario = validate_scenario_or_raise(scenario_payload)
    setup = bind_ontology_to_scenario(ontology, scenario)

    assert setup["space_summary"]["tech_space_actor_count"] == 2
    assert setup["space_summary"]["market_space_actor_count"] == 1
    assert setup["space_summary"]["shared_actor_count"] == 1
    assert setup["space_summary"]["adoption_resistance"] == 0.72
    assert setup["space_summary"]["incumbent_response_speed"] == 0.65
    assert setup["space_summary"]["value_perception_gap"] == 0.55
