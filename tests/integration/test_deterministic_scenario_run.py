import json
import sys
from pathlib import Path

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


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
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_cli_simulate_deterministic_pack_from_nl(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "det_result.json"
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
    assert payload["scenario_comparison"]["order"] == ["A", "B", "C"]
    assert payload["scenario_comparison"]["executed"] == ["A", "B", "C"]
    assert len(payload["scenario_results"]) == 3


def test_cli_compare_deterministic_pack_from_nl(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "det_compare.json"
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
