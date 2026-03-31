from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from omen.cli.main import main


class _FakeGeneration:
    def __init__(self, strategy_ontology: dict):
        self.strategy_ontology = strategy_ontology
        self.validation_passed = True
        self.validation_issues: list[dict] = []
        self.inferred_known_outcome = "unknown"


@pytest.fixture
def actor_case_file(tmp_path: Path) -> Path:
    case_dir = tmp_path / "cases" / "actors"
    case_dir.mkdir(parents=True, exist_ok=True)
    doc = case_dir / "xd.md"
    doc.write_text("actor narrative", encoding="utf-8")
    return doc


def test_actor_baseline_command_writes_required_artifacts(tmp_path: Path, actor_case_file: Path, monkeypatch) -> None:
    output_root = tmp_path / "output" / "actors"

    def _fake_strategy(**_: object) -> _FakeGeneration:
        return _FakeGeneration({"meta": {"case_id": "xd"}, "abox": {}})

    def _fake_actor(**_: object):
        payload = {
            "meta": {
                "case_id": "xd",
                "version": "v0.1.0-public",
                "disclosure_level": "public-structure",
                "strategic_dimensions": ["mental_patterns", "strategic_style"],
            },
            "actors": [
                {
                    "id": "a1",
                    "name": "Actor A",
                    "type": "role",
                    "profile": {
                        "mental_patterns": {"redacted": True},
                        "strategic_style": {"redacted": True},
                    },
                }
            ],
            "events": [{"id": "e1", "event": "launch", "time": "2016"}],
            "query_skeleton": {"query_types": ["status", "persona"]},
        }
        timeline = [{"id": "e1", "event": "launch", "description": "launch", "time": "2016"}]
        return payload, timeline

    monkeypatch.setattr("omen.cli.actor.generate_strategy_ontology_from_document", _fake_strategy)
    monkeypatch.setattr("omen.cli.actor.generate_actor_and_events_from_document", _fake_actor)
    monkeypatch.setattr(
        "omen.cli.actor.generate_persona_insight",
        lambda **_: {"persona_insight": {"narrative": "n", "key_traits": ["t1"]}, "run_meta": {"prompt_version": "v1"}},
    )
    monkeypatch.setattr(
        "omen.cli.actor.build_events_snapshot",
        lambda **_: {"timeline": [{"id": "e1", "time": "2016", "name": "launch", "description": "launch"}]},
    )
    monkeypatch.setattr("omen.cli.actor.ensure_analyze_prompt_available", lambda *_: None)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "analyze",
            "actor",
            "--doc",
            str(actor_case_file),
            "--output-dir",
            str(output_root),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    case_dir = output_root / "xd"
    assert (case_dir / "strategy_ontology.json").exists()
    assert (case_dir / "actor_ontology.json").exists()
    assert (case_dir / "analyze_status.json").exists()
    assert (case_dir / "analyze_persona.json").exists()

    actor_payload = json.loads((case_dir / "actor_ontology.json").read_text(encoding="utf-8"))
    assert actor_payload["meta"]["disclosure_level"] == "public-structure"
    assert actor_payload["meta"]["version"].endswith("-public")
    profile = actor_payload["actors"][0]["profile"]
    assert profile["mental_patterns"] == {"redacted": True}
    assert profile["strategic_style"] == {"redacted": True}


@pytest.mark.parametrize("subcommand", ["strategy", "insight"])
def test_actor_cloud_only_subcommands_return_guidance(tmp_path: Path, actor_case_file: Path, monkeypatch, capsys, subcommand: str) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "analyze",
            "actor",
            subcommand,
            "--doc",
            str(actor_case_file),
            "--output-dir",
            str(tmp_path / "output" / "actors"),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert "not available in this edition" in captured.out


def test_validate_actor_file_accepts_schema_with_extra_fields(tmp_path: Path, monkeypatch, capsys) -> None:
    payload = {
        "meta": {
            "case_id": "xd",
            "version": "v0.1.0-public",
            "disclosure_level": "public-structure",
            "strategic_dimensions": ["mental_patterns", "strategic_style"],
        },
        "actors": [
            {
                "id": "a1",
                "name": "Actor A",
                "type": "founder",
                "profile": {
                    "mental_patterns": {"redacted": True},
                    "strategic_style": {"redacted": True},
                },
            }
        ],
        "events": [],
        "influences": [{"source": "a1", "target": "e1", "type": "influences", "origin": "system_generated"}],
    }
    actor_file = tmp_path / "actor_ontology.json"
    actor_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["omen", "validate", "actor", "--file", str(actor_file)])

    with pytest.raises(SystemExit) as exc:
        main()

    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert '"status": "pass"' in captured.out
