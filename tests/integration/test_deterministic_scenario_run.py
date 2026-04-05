import json
import sys
from pathlib import Path

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"
NL_INPUT_PATH = ROOT / "tests" / "fixtures" / "scenario_compilation" / "nokia_nl_scenarios.json"


def test_cli_simulate_deterministic_pack_from_nl(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "det_result.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "simulate",
            "--scenario",
            str(SCENARIO_PATH),
            "--deterministic-nl-json",
            str(NL_INPUT_PATH),
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
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "compare",
            "--scenario",
            str(SCENARIO_PATH),
            "--deterministic-nl-json",
            str(NL_INPUT_PATH),
            "--output",
            str(output_path),
        ],
    )

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["comparison_type"] == "deterministic_pack"
    assert payload["comparability"]["comparable"] is True
