import json
import sys
from pathlib import Path

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_simulate_and_explain_default_to_output_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "simulate",
            "--scenario",
            str(SCENARIO_PATH),
        ],
    )
    main()

    result_path = tmp_path / "output" / "result.json"
    assert result_path.exists()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "explain",
            "--input",
            str(result_path),
        ],
    )
    main()

    explanation_path = tmp_path / "output" / "explanation.json"
    explanation = json.loads(explanation_path.read_text(encoding="utf-8"))
    assert explanation_path.exists()
    assert "narrative_summary" in explanation


def test_compare_defaults_to_output_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "compare",
            "--scenario",
            str(SCENARIO_PATH),
            "--overrides",
            '{"user_overlap_threshold": 0.9}',
        ],
    )

    main()

    comparison_path = tmp_path / "output" / "comparison.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    assert comparison_path.exists()
    assert "deltas" in comparison


def test_incremental_adds_timestamp_suffix_for_all_commands(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "simulate",
            "--scenario",
            str(SCENARIO_PATH),
            "--incremental",
        ],
    )
    main()

    simulate_files = list((tmp_path / "output").glob("result_*.json"))
    assert len(simulate_files) == 1

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "explain",
            "--input",
            str(simulate_files[0]),
            "--incremental",
        ],
    )
    main()

    explain_files = list((tmp_path / "output").glob("explanation_*.json"))
    assert len(explain_files) == 1

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "compare",
            "--scenario",
            str(SCENARIO_PATH),
            "--overrides",
            '{"user_overlap_threshold": 0.9}',
            "--incremental",
        ],
    )
    main()

    compare_files = list((tmp_path / "output").glob("comparison_*.json"))
    assert len(compare_files) == 1
