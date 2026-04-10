from argparse import Namespace
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


def test_handle_situation_analyze_command_url_flow(monkeypatch, tmp_path: Path, capsys) -> None:
    generated_case_path = tmp_path / "cases" / "situations" / "nokia_case.md"
    situation_output_path = tmp_path / "data" / "scenarios" / "nokia_v1" / "nokia_case_situation.json"

    monkeypatch.setattr(
        situation_cli,
        "analyze_and_save_situation_from_url",
        lambda **kwargs: {
            "source_text_path": tmp_path / "data" / "ingest" / "source" / "example.txt",
            "generated_case_path": generated_case_path,
            "artifact_path": situation_output_path,
            "markdown_path": situation_output_path.with_suffix(".md"),
            "generation_trace_path": situation_output_path.parent / "generation" / "log.json",
        },
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
    assert str(generated_case_path) in output
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
    )

    result = situation_cli.handle_situation_analyze_command(args)
    output = capsys.readouterr().out

    assert result == 2
    assert "use either --doc or --url, not both" in output


def test_handle_situation_analyze_command_uses_explicit_actor_ref(monkeypatch, tmp_path: Path) -> None:
    input_doc = tmp_path / "case.md"
    input_doc.write_text("example", encoding="utf-8")

    captured: dict[str, object] = {}

    monkeypatch.setattr(situation_cli, "_resolve_situation_doc_path", lambda raw: input_doc)
    monkeypatch.setattr(situation_cli, "validate_situation_source_or_raise", lambda path: None)
    monkeypatch.setattr(situation_cli, "_derive_default_pack_id", lambda input_path, actor_ref=None: "strategic_actor_case_v1")
    actor_json = tmp_path / "actor_ontology.json"
    actor_json.write_text("{}", encoding="utf-8")

    def _fake_analyze_and_save(**kwargs: object) -> dict[str, object]:
        captured["actor_ref"] = kwargs.get("actor_ref")
        output_path = kwargs["output_path"]
        assert isinstance(output_path, Path)
        return {
            "situation_artifact": {
                "version": "0.1.0",
                "id": "case",
                "context": {
                    "title": "Case",
                    "core_question": "Q",
                    "current_state": "S",
                    "core_dilemma": "D",
                    "key_decision_point": "K",
                    "target_outcomes": ["T"],
                    "hard_constraints": ["H"],
                    "known_unknowns": [],
                },
                "signals": [
                    {
                        "id": "sig_market_001",
                        "name": "Signal",
                        "domain": "market",
                        "strength": 0.6,
                        "direction": "up",
                        "mapped_targets": [
                            {
                                "space": "MarketSpace",
                                "element_key": "x",
                                "impact_type": "driver",
                                "impact_strength": 0.6,
                                "mechanism_conditions": {
                                    "activation_condition": "a",
                                    "expected_effect": "e",
                                },
                            }
                        ],
                        "cascade_rules": [],
                        "market_constraints": [
                            {
                                "constraint_key": "c",
                                "binding_strength": 0.5,
                            }
                        ],
                        "mechanism_note": "m",
                        "no_cascade_reason": "direct local effect in current horizon",
                    }
                ],
                "tech_space_seed": [],
                "market_space_seed": [],
                "uncertainty_space": {"overall_confidence": 0.6},
                "source_trace": [],
                "source_meta": {
                    "source_path": str(input_doc),
                    "generated_at": "2026-04-08T12:00:00",
                    "pack_id": "strategic_actor_case_v1",
                    "pack_version": "1.0.0",
                    "actor_ref": str(actor_json),
                },
            },
            "artifact_path": output_path,
            "markdown_path": output_path.with_suffix(".md"),
            "generation_trace_path": output_path.parent / "generation" / "log.json",
        }

    monkeypatch.setattr(situation_cli, "analyze_and_save_situation", _fake_analyze_and_save)

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
    assert captured["actor_ref"] == str(actor_json)


def test_handle_situation_analyze_command_rejects_missing_explicit_actor_ref(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    input_doc = tmp_path / "case.md"
    input_doc.write_text("example", encoding="utf-8")

    monkeypatch.setattr(situation_cli, "_resolve_situation_doc_path", lambda raw: input_doc)
    monkeypatch.setattr(situation_cli, "validate_situation_source_or_raise", lambda path: None)

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
    assert "actor reference not found" in output


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
        "analyze_and_save_situation",
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
        lambda situation_path, pack_id: scenario_output_path,
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
        lambda situation_path, pack_id: scenario_output_path,
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