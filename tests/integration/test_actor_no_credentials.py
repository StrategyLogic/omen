from __future__ import annotations

import os
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


def test_actor_baseline_runs_without_private_credentials(tmp_path: Path, monkeypatch) -> None:
    case_dir = tmp_path / "cases" / "actors"
    case_dir.mkdir(parents=True, exist_ok=True)
    doc = case_dir / "xd.md"
    doc.write_text("source", encoding="utf-8")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)

    monkeypatch.setattr("omen.cli.actor.generate_strategy_ontology_from_document", lambda **_: _FakeGeneration({"meta": {"case_id": "xd"}, "abox": {}}))
    monkeypatch.setattr(
        "omen.cli.actor.generate_actor_and_events_from_document",
        lambda **_: (
            {
                "meta": {"case_id": "xd", "version": "1.0.0"},
                "actors": [{"id": "a1", "shared_id": "a1"}],
                "events": [{"id": "e1", "event": "launch", "time": "2016"}],
                "query_skeleton": {"query_types": ["status", "persona"]},
            },
            [{"id": "e1", "event": "launch", "description": "launch", "time": "2016"}],
        ),
    )
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
        ["omen", "analyze", "actor", "--doc", str(doc), "--output-dir", str(tmp_path / "output" / "actors")],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    assert "OPENAI_API_KEY" not in os.environ
