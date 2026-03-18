import json
from pathlib import Path

from omen.scenario.case_replay_loader import load_case_replay_scenario


def test_load_case_replay_scenario_falls_back_for_us1(tmp_path: Path) -> None:
    payload = {
        "meta": {
            "version": "1.0",
            "case_id": "x-developer-replay",
            "domain": "management_ontology",
            "case_title": "X-Developer Replay",
        },
        "tbox": {
            "concepts": [
                {"name": "DataDrivenManagementActor", "description": "", "category": "actor"},
                {"name": "data_analysis", "description": "", "category": "capability"},
            ],
            "relations": [
                {
                    "name": "has_capability",
                    "source": "DataDrivenManagementActor",
                    "target": "data_analysis",
                    "description": "",
                }
            ],
            "axioms": [{"id": "ax-1", "statement": "sample", "type": "activation"}],
        },
        "abox": {
            "actors": [
                {"actor_id": "x_developer", "concept": "DataDrivenManagementActor"},
                {"actor_id": "pilot_team", "concept": "DataDrivenManagementActor"},
            ],
            "capabilities": [
                {"actor_id": "x_developer", "name": "data_analysis", "score": 0.9},
                {"actor_id": "pilot_team", "name": "data_analysis", "score": 0.7},
            ],
            "constraints": [],
        },
        "reasoning_profile": {"activation_rules": [{"rule_id": "ax-1"}]},
        "scenario_id": "bad-shape",
        "name": "bad-shape",
        "time_steps": 10,
        "actors": ["x_developer", "pilot_team"],
        "capabilities": ["data_analysis"],
    }

    ontology_path = tmp_path / "strategy_ontology.json"
    ontology_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    scenario, ontology_setup = load_case_replay_scenario(ontology_path)

    assert scenario.scenario_id
    assert len(scenario.actors) >= 2
    assert len(scenario.capabilities) >= 1
    assert ontology_setup["actor_count"] == 2


def test_load_case_replay_scenario_merges_missing_abox_actors(tmp_path: Path) -> None:
    payload = {
        "meta": {
            "version": "1.0",
            "case_id": "x-developer-replay",
            "domain": "management_ontology",
        },
        "tbox": {
            "concepts": [
                {"name": "DataDrivenManagementActor", "description": "", "category": "actor"},
                {"name": "data_analysis", "description": "", "category": "capability"},
            ],
            "relations": [
                {
                    "name": "has_capability",
                    "source": "DataDrivenManagementActor",
                    "target": "data_analysis",
                    "description": "",
                }
            ],
            "axioms": [{"id": "ax-1", "statement": "sample", "type": "activation"}],
        },
        "abox": {
            "actors": [
                {"actor_id": "x_developer", "concept": "DataDrivenManagementActor"},
                {"actor_id": "pilot_dev_team", "concept": "DataDrivenManagementActor"},
                {"actor_id": "broad_market_teams", "concept": "DataDrivenManagementActor"},
            ],
            "capabilities": [
                {"actor_id": "x_developer", "name": "data_analysis", "score": 0.9},
                {"actor_id": "pilot_dev_team", "name": "data_analysis", "score": 0.7},
                {"actor_id": "broad_market_teams", "name": "data_analysis", "score": 0.6},
            ],
            "constraints": [],
        },
        "reasoning_profile": {"activation_rules": [{"rule_id": "ax-1"}]},
        "scenario_id": "partial-scenario",
        "name": "partial-scenario",
        "time_steps": 10,
        "actors": ["x_developer"],
        "capabilities": ["data_analysis"],
    }

    ontology_path = tmp_path / "strategy_ontology.json"
    ontology_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    scenario, ontology_setup = load_case_replay_scenario(ontology_path)

    scenario_actor_ids = {actor.actor_id for actor in scenario.actors}
    assert {"x_developer", "pilot_dev_team", "broad_market_teams"}.issubset(scenario_actor_ids)
    assert ontology_setup["actor_count"] == 3
