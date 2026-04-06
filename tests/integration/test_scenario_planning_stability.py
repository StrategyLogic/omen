import json
import sys
from pathlib import Path

import pytest

from omen.cli.main import main


def _write_situation_artifact(path: Path) -> None:
    payload = {
        "version": "0.1.0",
        "id": "nokia-elop-2010",
        "context": {
            "title": "Nokia transition",
            "core_question": "Can platform reset work",
            "current_state": "Declining share",
            "core_dilemma": "speed vs continuity",
            "key_decision_point": "platform choice",
            "target_outcomes": ["recover position"],
            "hard_constraints": ["cash runway", "ecosystem inertia"],
            "known_unknowns": ["partner response"],
        },
        "signals": [{"name": "ecosystem fragmentation"}, {"name": "cash pressure"}],
        "tech_space_seed": [],
        "market_space_seed": [],
        "uncertainty_space": {"overall_confidence": 0.5},
        "source_trace": [{"source_path": "cases/situations/nokia-elop-2010.md"}],
        "source_meta": {
            "source_path": "cases/situations/nokia-elop-2010.md",
            "actor_ref": "actors/steve-jobs.md",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_scenario_planning_pack_id_input_stable_prior_order(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    pack_id = "strategic_actor_nokia_v1"
    situation_path = tmp_path / "data" / "scenarios" / pack_id / "situation.json"
    _write_situation_artifact(situation_path)

    fake_decomposition = {
        "pack_id": pack_id,
        "pack_version": "1.0.0",
        "derived_from_situation_id": "nokia-elop-2010",
        "ontology_version": "scenario_ontology_v1",
        "raw_prior_scores": [
            {"scenario_key": "A", "score": 0.4},
            {"scenario_key": "B", "score": 0.35},
            {"scenario_key": "C", "score": 0.25},
        ],
        "scenarios": [
            {
                "scenario_key": "A",
                "title": "A",
                "goal": "gA",
                "target": "tA",
                "objective": "oA",
                "variables": [{"name": "x", "type": "categorical"}],
                "constraints": ["c"],
                "tradeoff_pressure": ["t"],
                "resistance_assumptions": {
                    "structural_conflict": 0.8,
                    "resource_reallocation_drag": 0.7,
                    "cultural_misalignment": 0.6,
                    "veto_node_intensity": 0.7,
                    "aggregate_resistance": 0.7,
                    "assumption_rationale": ["r"],
                },
                "modeling_notes": ["n"],
            },
            {
                "scenario_key": "B",
                "title": "B",
                "goal": "gB",
                "target": "tB",
                "objective": "oB",
                "variables": [{"name": "x", "type": "categorical"}],
                "constraints": ["c"],
                "tradeoff_pressure": ["t"],
                "resistance_assumptions": {
                    "structural_conflict": 0.5,
                    "resource_reallocation_drag": 0.5,
                    "cultural_misalignment": 0.5,
                    "veto_node_intensity": 0.4,
                    "aggregate_resistance": 0.475,
                    "assumption_rationale": ["r"],
                },
                "modeling_notes": ["n"],
            },
            {
                "scenario_key": "C",
                "title": "C",
                "goal": "gC",
                "target": "tC",
                "objective": "oC",
                "variables": [{"name": "x", "type": "categorical"}],
                "constraints": ["c"],
                "tradeoff_pressure": ["t"],
                "resistance_assumptions": {
                    "structural_conflict": 0.4,
                    "resource_reallocation_drag": 0.4,
                    "cultural_misalignment": 0.5,
                    "veto_node_intensity": 0.3,
                    "aggregate_resistance": 0.4,
                    "assumption_rationale": ["r"],
                },
                "modeling_notes": ["n"],
            },
        ],
    }

    monkeypatch.setattr(
        "omen.scenario.planner.decompose_scenario_from_situation",
        lambda **_: fake_decomposition,
    )

    for _ in range(2):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "omen",
                "scenario",
                "--situation",
                pack_id,
            ],
        )
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    prior_snapshot_path = tmp_path / "data" / "scenarios" / pack_id / "traces" / "prior_snapshot.json"
    scenario_path = tmp_path / "data" / "scenarios" / pack_id / "scenario_pack.json"

    assert prior_snapshot_path.exists()
    assert scenario_path.exists()

    prior_payload = json.loads(prior_snapshot_path.read_text(encoding="utf-8"))
    ordered = [item["scenario_key"] for item in prior_payload["normalized_priors"]]
    assert ordered == ["A", "B", "C"]

    scenario_payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    assert scenario_payload["planning_query_ref"].endswith("planning_query.json")
    assert scenario_payload["prior_snapshot_ref"].endswith("prior_snapshot.json")
