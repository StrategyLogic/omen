from argparse import Namespace
from pathlib import Path

import omen.cli.situation as situation_cli
from omen.ingest.processor.url import save_url_source_text
from omen.ingest.synthesizer.services.situation import LLMJsonValidationAbort
from omen.scenario.planner import ScenarioDecompositionValidationError


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
    monkeypatch.setattr(situation_cli, "save_situation_markdown", lambda path, payload, config_path=None: path)
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


def test_handle_situation_analyze_command_exits_gracefully_on_invalid_enhance_json(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    input_doc = tmp_path / "case.md"
    input_doc.write_text("example", encoding="utf-8")

    monkeypatch.setattr(situation_cli, "_resolve_situation_doc_path", lambda raw: input_doc)
    monkeypatch.setattr(situation_cli, "validate_situation_source_or_raise", lambda path: None)
    monkeypatch.setattr(situation_cli, "_derive_default_pack_id", lambda input_path, actor_ref=None: "case_v1")
    monkeypatch.setattr(
        situation_cli,
        "analyze_situation_document",
        lambda **kwargs: (_ for _ in ()).throw(
            LLMJsonValidationAbort(
                stage="situation_enhance_prompt",
                reason="LLM response does not contain JSON object",
            )
        ),
    )

    args = Namespace(
        doc="case",
        input=None,
        url=None,
        actor=None,
        output=None,
        pack_id=None,
        pack_version="1.0.0",
        config="config/llm.toml",
    )

    result = situation_cli.handle_situation_analyze_command(args)
    output = capsys.readouterr().out

    assert result == 2
    assert "LLM JSON validation aborted by policy" in output
    assert "Exiting without retry/fallback" in output


def test_handle_scenario_command_writes_non_json_llm_output(monkeypatch, tmp_path: Path, capsys) -> None:
    scenario_output_path = tmp_path / "data" / "scenarios" / "sap_v1" / "scenario_pack.json"

    monkeypatch.setattr(situation_cli, "resolve_situation_artifact_ref", lambda ref: tmp_path / "situation.json")
    (tmp_path / "situation.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        situation_cli,
        "load_situation_artifact",
        lambda path: {"source_meta": {"actor_ref": "actors/steve-jobs.md", "source_path": "cases/situations/sap.md"}},
    )
    monkeypatch.setattr(situation_cli, "_derive_pack_id_from_situation_artifact", lambda artifact, path: "sap_v1")
    monkeypatch.setattr(
        situation_cli,
        "_resolve_splitter_default_output_path",
        lambda situation_path, pack_id: scenario_output_path,
    )
    monkeypatch.setattr(
        situation_cli,
        "plan_scenarios_from_situation",
        lambda **kwargs: (_ for _ in ()).throw(
            LLMJsonValidationAbort(
                stage="situation_decompose_prompt",
                reason="LLM response does not contain JSON object",
                raw_output="not-json-output",
                retry_output="still-not-json",
            )
        ),
    )

    args = Namespace(
        situation="sap_v1",
        output=None,
        pack_id=None,
        pack_version="1.0.0",
        actor=None,
        config="config/llm.toml",
    )

    result = situation_cli.handle_scenario_command(args)
    output = capsys.readouterr().out

    output_file = tmp_path / "data" / "scenarios" / "sap_v1" / "generation" / "output.txt"
    generation_trace_file = tmp_path / "data" / "scenarios" / "sap_v1" / "generation" / "log.json"
    assert result == 2
    assert output_file.exists()
    assert generation_trace_file.exists()
    written = output_file.read_text(encoding="utf-8")
    assert "[raw_output]" in written
    assert "not-json-output" in written
    assert "[retry_output]" in written
    assert "still-not-json" in written
    assert "Scenario debug output saved to" in output


def test_handle_scenario_command_writes_output_for_generic_validation_failure(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    scenario_output_path = tmp_path / "data" / "scenarios" / "sap_v1" / "scenario_pack.json"

    monkeypatch.setattr(situation_cli, "resolve_situation_artifact_ref", lambda ref: tmp_path / "situation.json")
    (tmp_path / "situation.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        situation_cli,
        "load_situation_artifact",
        lambda path: {"source_meta": {"actor_ref": "actors/steve-jobs.md", "source_path": "cases/situations/sap.md"}},
    )
    monkeypatch.setattr(situation_cli, "_derive_pack_id_from_situation_artifact", lambda artifact, path: "sap_v1")
    monkeypatch.setattr(
        situation_cli,
        "_resolve_splitter_default_output_path",
        lambda situation_path, pack_id: scenario_output_path,
    )
    monkeypatch.setattr(
        situation_cli,
        "plan_scenarios_from_situation",
        lambda **kwargs: (_ for _ in ()).throw(
            ScenarioDecompositionValidationError(
                "Scenario decomposition validation failed: `scenarios` must be a JSON array",
                decomposition_payload={"scenarios": "invalid"},
            )
        ),
    )

    args = Namespace(
        situation="sap_v1",
        output=None,
        pack_id=None,
        pack_version="1.0.0",
        actor=None,
        config="config/llm.toml",
    )

    result = situation_cli.handle_scenario_command(args)
    output = capsys.readouterr().out

    output_file = tmp_path / "data" / "scenarios" / "sap_v1" / "generation" / "output.txt"
    generation_trace_file = tmp_path / "data" / "scenarios" / "sap_v1" / "generation" / "log.json"
    assert result == 2
    assert output_file.exists()
    assert generation_trace_file.exists()
    written = output_file.read_text(encoding="utf-8")
    assert "stage: scenario_planning" in written
    assert "scenarios` must be a JSON array" in written
    assert "[raw_output]" in written
    assert '"scenarios": "invalid"' in written
    assert "Scenario debug output saved to" in output