import json
import sys
from pathlib import Path

import pytest

from omen.cli.main import main


def _write_case_artifacts(output_root: Path, case_id: str = "xd") -> Path:
    case_dir = output_root / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    founder_payload = {
        "meta": {"case_id": case_id},
        "actors": [
            {
                "id": "founder-1",
                "type": "founder",
                "name": "Founder X",
                "profile": {
                    "mental_patterns": {"core_beliefs": ["data is truth"]},
                    "strategic_style": {
                        "decision_style": "evidence-based",
                        "non_negotiables": ["no manual reporting"],
                    },
                },
            }
        ],
        "events": [
            {
                "id": "event-1",
                "name": "Launch",
                "date": "2016",
                "description": "Launches workflow product",
                "actors_involved": ["founder-1"],
                "evidence_refs": ["event-1"],
            },
            {
                "id": "event-2",
                "name": "Pilot",
                "date": "2017",
                "description": "Runs pilot with customers",
                "actors_involved": ["founder-1"],
                "evidence_refs": ["event-2"],
            },
            {
                "id": "event-3",
                "name": "Pricing",
                "date": "2018",
                "description": "Introduces pricing updates",
                "actors_involved": ["founder-1"],
                "evidence_refs": ["event-3"],
            },
        ],
        "constraints": [{"id": "constraint-1", "name": "cash flow", "applies_to": ["founder-1"]}],
        "influences": [],
    }
    strategy_payload = {"meta": {"case_id": case_id, "known_outcome": "Adoption remained gradual."}}

    (case_dir / "founder_ontology.json").write_text(
        json.dumps(founder_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (case_dir / "strategy_ontology.json").write_text(
        json.dumps(strategy_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return case_dir


def test_case_analyze_persona_writes_output(tmp_path: Path, monkeypatch) -> None:
    output_root = tmp_path / "output" / "case_replay"
    case_dir = _write_case_artifacts(output_root)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "case",
            "analyze",
            "persona",
            "--case-id",
            "xd",
            "--output-dir",
            str(output_root),
            "--config",
            str(tmp_path / "missing-llm.toml"),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    payload = json.loads((case_dir / "analyze_persona.json").read_text(encoding="utf-8"))
    assert payload["query"]["type"] == "persona"
    assert "persona_insight" in payload
    assert payload["run_meta"]["prompt_version"] == "v2.0-persona-open"


def test_case_analyze_why_writes_output(tmp_path: Path, monkeypatch) -> None:
    output_root = tmp_path / "output" / "case_replay"
    case_dir = _write_case_artifacts(output_root)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "case",
            "analyze",
            "why",
            "--case-id",
            "xd",
            "--decision-id",
            "event-2",
            "--output-dir",
            str(output_root),
            "--config",
            str(tmp_path / "missing-llm.toml"),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    payload = json.loads((case_dir / "analyze_why.json").read_text(encoding="utf-8"))
    assert payload["query"]["type"] == "why"
    assert payload["query"]["decision_id"] == "event-2"
    assert len(payload["why_chain"]) >= 3
    assert payload["run_meta"]["prompt_version"] == "v2.0-why-pro"


def test_case_analyze_formation_fails_when_pro_prompt_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    output_root = tmp_path / "output" / "case_replay"
    _write_case_artifacts(output_root)

    def _raise_unavailable(command: str):
        raise FileNotFoundError(f"missing prompt pack for {command}")

    monkeypatch.setattr("omen.cli.case.ensure_analyze_prompt_available", _raise_unavailable)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "case",
            "analyze",
            "formation",
            "--case-id",
            "xd",
            "--event-id",
            "event-1",
            "--output-dir",
            str(output_root),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 2