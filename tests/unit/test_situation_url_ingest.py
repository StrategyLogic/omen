from argparse import Namespace
import json
from pathlib import Path

import omen.cli.situation as situation_cli
from omen.ingest.processor.url import save_url_source_text
from omen.ingest.synthesizer.services.errors import LLMJsonValidationAbort
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


def test_handle_situation_analyze_command_url_flow(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        situation_cli,
        "run_situation_analysis",
        lambda **kwargs: None,
    )

    args = Namespace(
        doc=None,
        input=None,
        url="https://example.com/articles/nokia-turnaround",
        actor=None,
        output=None,
        pack_id=None,
        pack_version="1.0.0",
    )

    result = situation_cli.handle_situation_analyze_command(args)
    output = capsys.readouterr().out

    assert result == 0
    assert "Situation analysis started" in output
    assert "Situation analysis completed" in output


def test_handle_situation_analyze_command_rejects_doc_and_url_together(capsys) -> None:
    args = Namespace(
        doc="nokia-elop-2010",
        input=None,
        url="https://example.com/articles/nokia-turnaround",
        actor=None,
        output=None,
        pack_id=None,
        pack_version="1.0.0",
    )

    result = situation_cli.handle_situation_analyze_command(args)
    output = capsys.readouterr().out

    assert result == 2
    assert "Situation analysis started" in output
    assert "Situation analysis failed:" in output


def test_handle_situation_analyze_command_uses_explicit_actor_ref(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    actor_json = tmp_path / "actor_ontology.json"
    actor_json.write_text("{}", encoding="utf-8")

    def _fake_run(**kwargs: object) -> None:
        captured["actor"] = kwargs.get("actor")

    monkeypatch.setattr(situation_cli, "run_situation_analysis", _fake_run)

    args = Namespace(
        doc="case",
        input=None,
        url=None,
        actor=str(actor_json),
        output=str(tmp_path / "situation.json"),
        pack_id=None,
        pack_version="1.0.0",
    )

    result = situation_cli.handle_situation_analyze_command(args)
    assert result == 0
    assert captured["actor"] == str(actor_json)


def test_handle_situation_analyze_command_rejects_missing_explicit_actor_ref(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        situation_cli,
        "run_situation_analysis",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("actor reference not found")),
    )

    args = Namespace(
        doc="case",
        input=None,
        url=None,
        actor="actors/missing.md",
        output=str(tmp_path / "situation.json"),
        pack_id=None,
        pack_version="1.0.0",
    )

    result = situation_cli.handle_situation_analyze_command(args)
    output = capsys.readouterr().out
    assert result == 2
    assert "Situation analysis failed: actor reference not found" in output


def test_handle_situation_analyze_command_exits_gracefully_on_invalid_enhance_json(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        situation_cli,
        "run_situation_analysis",
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
        lambda pack_id: scenario_output_path,
    )
    monkeypatch.setattr(
        situation_cli,
        "from_situation",
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
        lambda pack_id: scenario_output_path,
    )
    monkeypatch.setattr(
        situation_cli,
        "from_situation",
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


def test_append_scenario_trace_preserves_existing_fields_and_appends_history(tmp_path: Path) -> None:
    trace_path = tmp_path / "generation" / "log.json"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        json.dumps(
            {
                "artifact_type": "situation_generation_trace",
                "situation_id": "sap_reltio_acquisition",
                "confidence": {"overall_confidence": 0.7},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    situation_cli._append_scenario_decomposition_trace(  # pylint: disable=protected-access
        trace_path=trace_path,
        scenario_artifact_path=Path("data/scenarios/sap_v1/scenario_pack.json"),
        situation_ref=Path("data/scenarios/sap_v1/situation.json"),
        decomposition_quality={
            "schema_completeness_percent": 100.0,
            "logic_usable": True,
            "retries": 0,
            "validation_issues": [],
            "logic_issues": [],
        },
        planner_trace={
            "actor_style_enhancement": {"status": "noop"},
            "prior_scoring": {"status": "ok", "scoring_source": "llm"},
        },
    )

    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    assert payload["situation_id"] == "sap_reltio_acquisition"
    assert payload["confidence"]["overall_confidence"] == 0.7
    assert payload["scenario_decomposition"]["logic_usable"] is True
    assert payload["scenario_planner"]["prior_scoring"]["scoring_source"] == "llm"
    assert isinstance(payload.get("trace_history"), list)
    assert len(payload["trace_history"]) == 1
    assert payload["trace_history"][0]["stage"] == "scenario_decomposition"
    assert payload["trace_history"][0]["status"] == "ok"


def test_failure_trace_preserves_existing_fields_and_appends_history(tmp_path: Path) -> None:
    trace_path = tmp_path / "generation" / "log.json"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        json.dumps(
            {
                "artifact_type": "situation_generation_trace",
                "situation_id": "sap_reltio_acquisition",
                "validation_passed": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    situation_cli._write_scenario_failure_trace(  # pylint: disable=protected-access
        trace_path=trace_path,
        situation_ref=Path("data/scenarios/sap_v1/situation.json"),
        stage="scenario_planning",
        reason="validation failed",
    )

    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    assert payload["situation_id"] == "sap_reltio_acquisition"
    assert payload["validation_passed"] is True
    assert payload["scenario_decomposition"]["status"] == "failed"
    assert payload["scenario_decomposition"]["validation_issues"] == ["validation failed"]
    assert isinstance(payload.get("trace_history"), list)
    assert len(payload["trace_history"]) == 1
    assert payload["trace_history"][0]["stage"] == "scenario_planning"
    assert payload["trace_history"][0]["status"] == "failed"