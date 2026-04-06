from argparse import Namespace
from pathlib import Path

import omen.cli.situation as situation_cli
from omen.ingest.processor.url import save_url_source_text


def test_save_url_source_text_writes_under_ingest_source(tmp_path: Path) -> None:
    output_path = save_url_source_text(
        url="https://example.com/articles/nokia-turnaround",
        text="Nokia article body",
        source_dir=tmp_path,
    )

    assert output_path.parent == tmp_path
    assert output_path.name == "example-com-articles-nokia-turnaround.txt"
    assert output_path.read_text(encoding="utf-8") == "Nokia article body"


def test_handle_situation_analyze_command_url_flow(monkeypatch, tmp_path: Path, capsys) -> None:
    generated_case_path = tmp_path / "cases" / "situations" / "nokia_case.md"
    situation_output_path = tmp_path / "data" / "scenarios" / "nokia_v1" / "nokia_case_situation.json"

    monkeypatch.setattr(situation_cli, "fetch_url_text", lambda url: "Fetched article text")
    monkeypatch.setattr(
        situation_cli,
        "save_url_source_text",
        lambda *, url, text: tmp_path / "data" / "ingest" / "source" / "example.txt",
    )
    monkeypatch.setattr(
        situation_cli,
        "generate_situation_case_document",
        lambda *, source_text, source_ref, source_text_path, config_path: ("nokia_case", "# Nokia Case\n\nBody\n"),
    )
    monkeypatch.setattr(situation_cli, "_resolve_generated_case_path", lambda case_name: generated_case_path)
    monkeypatch.setattr(situation_cli, "validate_situation_source_or_raise", lambda path: None)
    monkeypatch.setattr(situation_cli, "_derive_default_pack_id", lambda input_path, actor_ref=None: "nokia_v1")
    monkeypatch.setattr(situation_cli, "_resolve_default_output_path", lambda input_path, pack_id: situation_output_path)
    monkeypatch.setattr(
        situation_cli,
        "analyze_situation_document",
        lambda **kwargs: {
            "version": "0.1.0",
            "id": "nokia_case",
            "context": {
                "title": "Nokia Case",
                "core_question": "What next?",
                "current_state": "State",
                "core_dilemma": "Dilemma",
                "key_decision_point": "Decision",
                "target_outcomes": ["Outcome"],
                "hard_constraints": ["Constraint"],
                "known_unknowns": ["Unknown"],
            },
            "signals": [{"name": "Signal"}],
            "uncertainty_space": {"confidence_risk": 0.4, "confidence_overall": 0.7, "metrics": {"cognitive_coverage": 0.5}},
            "source_meta": {"source_path": str(generated_case_path), "generated_at": "2026-04-05T12:00:00", "pack_id": "nokia_v1", "pack_version": "1.0.0"},
            "source_trace": [{"source_path": str(generated_case_path), "situation_id": "nokia_case"}],
        },
    )
    monkeypatch.setattr(situation_cli, "save_situation_artifact", lambda path, payload: situation_output_path)
    monkeypatch.setattr(
        situation_cli,
        "save_situation_markdown",
        lambda path, payload, config_path=None: path,
    )
    monkeypatch.setattr(situation_cli, "build_situation_confidence_trace", lambda **kwargs: {"artifact_type": "situation_generation_trace"})
    monkeypatch.setattr(situation_cli, "save_auxiliary_json", lambda path, payload: path)

    args = Namespace(
        doc=None,
        input=None,
        url="https://example.com/articles/nokia-turnaround",
        actor=None,
        output=None,
        pack_id=None,
        pack_version="1.0.0",
        config="config/llm.toml",
    )

    result = situation_cli.handle_situation_analyze_command(args)
    output = capsys.readouterr().out

    assert result == 0
    assert generated_case_path.exists()
    assert "Using URL source for situation analysis..." in output
    assert "URL fetch: SUCCESS" in output
    assert "Generated situation case: SUCCESS" in output
    assert "Saved situation artifact to" in output


def test_handle_situation_analyze_command_rejects_doc_and_url_together(capsys) -> None:
    args = Namespace(
        doc="nokia-elop-2010",
        input=None,
        url="https://example.com/articles/nokia-turnaround",
        actor=None,
        output=None,
        pack_id=None,
        pack_version="1.0.0",
        config="config/llm.toml",
    )

    result = situation_cli.handle_situation_analyze_command(args)
    output = capsys.readouterr().out

    assert result == 2
    assert "use either --doc or --url, not both" in output