import json
import sys
from pathlib import Path

import pytest

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SITUATION_INPUT = ROOT / "cases" / "situations" / "nokia-elop-2010.md"
ACTOR_REF = "actors/steve-jobs.md"


def test_analyze_situation_then_simulate_happy_path(tmp_path: Path, monkeypatch) -> None:
    situation_output = tmp_path / "nokia_situation.json"
    situation_summary = tmp_path / "nokia_situation.md"
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
            str(situation_output),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0

    assert situation_output.exists()
    assert situation_summary.exists()
    situation_payload = json.loads(situation_output.read_text(encoding="utf-8"))
    assert situation_payload["version"] == "0.1.0"
    assert situation_payload["signals"]

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "scenario",
            "--situation",
            str(situation_output),
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
    situation_output = tmp_path / "nokia_no_actor_situation.json"
    situation_summary = tmp_path / "nokia_no_actor_situation.md"
    scenario_output = tmp_path / "nokia_no_actor_scenario.json"

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
            str(situation_output),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert situation_output.exists()
    assert situation_summary.exists()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "scenario",
            "--situation",
            str(situation_output),
            "--output",
            str(scenario_output),
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0

    assert scenario_output.exists()
    scenario_summary = scenario_output.with_suffix(".md")
    assert scenario_summary.exists()

    payload = json.loads(scenario_output.read_text(encoding="utf-8"))
    keys = [item["scenario_key"] for item in payload["scenarios"]]
    assert keys == ["A", "B", "C"]


def test_analyze_situation_filename_resolves_cases_folder(tmp_path: Path, monkeypatch) -> None:
    situation_output = tmp_path / "nokia_by_filename_situation.json"

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
            str(situation_output),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert situation_output.exists()


def test_analyze_situation_doc_without_md_suffix(tmp_path: Path, monkeypatch) -> None:
    situation_output = tmp_path / "nokia_no_suffix_situation.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "analyze",
            "situation",
            "--doc",
            "nokia-elop-2010",
            "--output",
            str(situation_output),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert situation_output.exists()


def test_analyze_situation_defaults_output_under_data_scenarios(monkeypatch) -> None:
    default_json = Path("data/scenarios/nokia_v1/nokia-elop-2010_situation.json")
    default_md = Path("data/scenarios/nokia_v1/nokia-elop-2010_situation.md")
    backup_json = default_json.read_text(encoding="utf-8") if default_json.exists() else None
    backup_md = default_md.read_text(encoding="utf-8") if default_md.exists() else None

    try:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "omen",
                "analyze",
                "situation",
                "--doc",
                "nokia-elop-2010.md",
            ],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        assert default_json.exists()
        assert default_md.exists()
    finally:
        if backup_json is None and default_json.exists():
            default_json.unlink()
        elif backup_json is not None:
            default_json.write_text(backup_json, encoding="utf-8")

        if backup_md is None and default_md.exists():
            default_md.unlink()
        elif backup_md is not None:
            default_md.write_text(backup_md, encoding="utf-8")


def test_scenario_command_defaults_output_under_data_scenario_pack(monkeypatch) -> None:
    situation_default_json = Path("data/scenarios/nokia_v1/nokia-elop-2010_situation.json")
    default_json = Path("data/scenarios/nokia_v1/nokia-elop-2010.json")
    default_md = Path("data/scenarios/nokia_v1/nokia-elop-2010.md")
    situation_backup_json = (
        situation_default_json.read_text(encoding="utf-8")
        if situation_default_json.exists()
        else None
    )
    backup_json = default_json.read_text(encoding="utf-8") if default_json.exists() else None
    backup_md = default_md.read_text(encoding="utf-8") if default_md.exists() else None

    try:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "omen",
                "analyze",
                "situation",
                "--doc",
                "nokia-elop-2010.md",
            ],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        assert situation_default_json.exists()

        monkeypatch.setattr(
            sys,
            "argv",
            [
                "omen",
                "scenario",
                "--situation",
                str(situation_default_json),
            ],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        assert default_json.exists()
        assert default_md.exists()
        payload = json.loads(default_json.read_text(encoding="utf-8"))
        keys = [item["scenario_key"] for item in payload["scenarios"]]
        assert keys == ["A", "B", "C"]
    finally:
        if situation_backup_json is None and situation_default_json.exists():
            situation_default_json.unlink()
        elif situation_backup_json is not None:
            situation_default_json.write_text(situation_backup_json, encoding="utf-8")

        if backup_json is None and default_json.exists():
            default_json.unlink()
        elif backup_json is not None:
            default_json.write_text(backup_json, encoding="utf-8")

        if backup_md is None and default_md.exists():
            default_md.unlink()
        elif backup_md is not None:
            default_md.write_text(backup_md, encoding="utf-8")
