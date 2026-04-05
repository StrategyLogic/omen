import json
import sys
from pathlib import Path

import pytest

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SITUATION_INPUT = ROOT / "cases" / "situations" / "nokia-elop-2010.md"


def _prepare_scenario_artifact(tmp_path: Path, monkeypatch) -> Path:
    situation_output = tmp_path / "situation.json"
    scenario_output = tmp_path / "scenario.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "analyze",
            "situation",
            "--doc",
            str(SITUATION_INPUT),
            "--actor",
            "actors/steve-jobs.md",
            "--output",
            str(situation_output),
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0

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

    return scenario_output


def test_derivation_trace_completeness(tmp_path: Path, monkeypatch) -> None:
    scenario_output = _prepare_scenario_artifact(tmp_path, monkeypatch)
    result_output = tmp_path / "result.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "simulate",
            "--scenario",
            str(scenario_output),
            "--output",
            str(result_output),
        ],
    )
    main()

    payload = json.loads(result_output.read_text(encoding="utf-8"))
    for item in payload["scenario_results"]:
        assert "selected_dimensions" in item
        assert item["selected_dimensions"]["selection_rationale"]
        assert "derivation_trace" in item
        assert item["derivation_trace"]["derivation_steps"]


def test_partial_evidence_confidence_behavior(tmp_path: Path, monkeypatch) -> None:
    scenario_output = _prepare_scenario_artifact(tmp_path, monkeypatch)
    result_output = tmp_path / "result.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "simulate",
            "--scenario",
            str(scenario_output),
            "--output",
            str(result_output),
        ],
    )
    main()

    payload = json.loads(result_output.read_text(encoding="utf-8"))
    for item in payload["scenario_results"]:
        assert item["confidence_level"] == "reduced-confidence"
        reasons = item["derivation_trace"].get("missing_evidence_reasons") or []
        assert reasons
