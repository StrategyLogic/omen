import json
import sys
from pathlib import Path

from omen import __version__
from omen.cli.main import main


def test_package_version_is_defined() -> None:
    assert __version__ == "0.2.1"


def test_smoke_deterministic_simulate_cli(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "smoke_deterministic_result.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "simulate",
            "--scenario",
            "data/scenarios/ontology.json",
            "--deterministic-nl-json",
            "tests/fixtures/scenario_compilation/nokia_nl_scenarios.json",
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
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "compare",
            "--scenario",
            "data/scenarios/ontology.json",
            "--deterministic-nl-json",
            "tests/fixtures/scenario_compilation/nokia_nl_scenarios.json",
            "--output",
            str(output_path),
        ],
    )

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["comparison_type"] == "deterministic_pack"
    assert payload["comparability"]["comparable"] is True
