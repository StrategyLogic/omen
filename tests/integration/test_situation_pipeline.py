import json
import sys
from pathlib import Path

import pytest

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SITUATION_INPUT = ROOT / "cases" / "situations" / "nokia-elop-2010.md"
ACTOR_REF = "actors/steve-jobs.md"


def test_analyze_situation_then_simulate_happy_path(tmp_path: Path, monkeypatch) -> None:
    scenario_output = tmp_path / "nokia_scenario.json"
    scenario_summary = tmp_path / "nokia_scenario.md"
    sim_output = tmp_path / "det_result.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "analyze",
            "situation",
            "--doc",
            "nokia-elop-2010.md",
            "--actor",
            ACTOR_REF,
            "--output",
            str(scenario_output),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0

    assert scenario_output.exists()
    assert scenario_summary.exists()
    scenario_payload = json.loads(scenario_output.read_text(encoding="utf-8"))
    keys = [item["scenario_key"] for item in scenario_payload["scenarios"]]
    assert keys == ["A", "B", "C"]
    summary_text = scenario_summary.read_text(encoding="utf-8")
    assert "# Scenario Ontology:" in summary_text
    assert "## Scenario A:" in summary_text

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "simulate",
            "--scenario",
            str(scenario_output),
            "--output",
            str(sim_output),
        ],
    )

    main()

    payload = json.loads(sim_output.read_text(encoding="utf-8"))
    assert payload["scenario_comparison"]["order"] == ["A", "B", "C"]
    assert payload["scenario_comparison"]["executed"] == ["A", "B", "C"]
    assert len(payload["scenario_results"]) == 3


def test_simulate_rejects_missing_required_slot(tmp_path: Path, monkeypatch) -> None:
    bad_ontology = {
        "pack_id": "strategic_actor_nokia_v1",
        "pack_version": "1.0.0",
        "derived_from_situation_id": "missing-c",
        "ontology_version": "scenario_ontology_v1",
        "scenarios": [
            {
                "scenario_key": "A",
                "title": "A",
                "objective": "A objective",
                "constraints": ["c1"],
                "tradeoff_pressure": ["t1"],
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
                "objective": "B objective",
                "constraints": ["c1"],
                "tradeoff_pressure": ["t1"],
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
        ],
    }

    bad_path = tmp_path / "bad_scenario.json"
    bad_path.write_text(json.dumps(bad_ontology, ensure_ascii=False, indent=2), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "simulate",
            "--scenario",
            str(bad_path),
            "--output",
            str(tmp_path / "unused.json"),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2


def test_analyze_situation_without_actor_happy_path(tmp_path: Path, monkeypatch) -> None:
    scenario_output = tmp_path / "nokia_no_actor.json"
    scenario_summary = tmp_path / "nokia_no_actor.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "analyze",
            "situation",
            "--doc",
            str(SITUATION_INPUT),
            "--output",
            str(scenario_output),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert scenario_output.exists()
    assert scenario_summary.exists()

    payload = json.loads(scenario_output.read_text(encoding="utf-8"))
    keys = [item["scenario_key"] for item in payload["scenarios"]]
    assert keys == ["A", "B", "C"]


def test_analyze_situation_filename_resolves_cases_folder(tmp_path: Path, monkeypatch) -> None:
    scenario_output = tmp_path / "nokia_by_filename.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "analyze",
            "situation",
            "--doc",
            "nokia-elop-2010.md",
            "--output",
            str(scenario_output),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert scenario_output.exists()
