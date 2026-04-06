import json
import sys
from pathlib import Path

from omen import __version__
from omen.cli.main import main


def _write_ontology(path: Path) -> None:
    payload = {
        "pack_id": "strategic_actor_nokia_v1",
        "pack_version": "1.0.0",
        "derived_from_situation_id": "nokia-elop-2010",
        "ontology_version": "scenario_ontology_v1",
        "planning_query_ref": "traces/planning_query.json",
        "prior_snapshot_ref": "traces/prior_snapshot.json",
        "scenarios": [
            {
                "scenario_key": "A",
                "title": "Scenario A",
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
                "title": "Scenario B",
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
                "title": "Scenario C",
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
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_package_version_is_defined() -> None:
    assert __version__ == "0.1.0"


def test_smoke_deterministic_simulate_cli(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "smoke_deterministic_result.json"
    scenario_path = tmp_path / "scenario_pack.json"
    _write_ontology(scenario_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "simulate",
            "--scenario",
            str(scenario_path),
            "--output",
            str(output_path),
        ],
    )

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["export_status"] == "success"
    assert payload["scenario_comparison"]["executed"] == ["A", "B", "C"]


def test_smoke_deterministic_compare_cli(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "smoke_deterministic_compare.json"
    scenario_path = tmp_path / "scenario_pack.json"
    _write_ontology(scenario_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "compare",
            "--scenario",
            str(scenario_path),
            "--output",
            str(output_path),
        ],
    )

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["comparison_type"] == "deterministic_pack"
    assert payload["comparability"]["comparable"] is True
