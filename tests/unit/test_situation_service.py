from pathlib import Path

import pytest

import omen.ingest.synthesizer.services.situation as situation_service


class _DummyValidated:
    def __init__(self, payload: dict):
        self._payload = payload

    def model_dump(self) -> dict:
        return self._payload


def test_save_and_load_situation_artifact_roundtrip(monkeypatch, tmp_path: Path) -> None:
    def _validate(payload: dict) -> _DummyValidated:
        return _DummyValidated(payload)

    monkeypatch.setattr(
        situation_service,
        "validate_situation_artifact_or_raise",
        _validate,
    )

    payload = {"id": "case", "version": "0.1.0", "context": {"title": "Case"}}
    output_path = tmp_path / "data" / "scenarios" / "case_v1" / "situation.json"

    written = situation_service.save_situation_artifact(output_path, payload)
    loaded = situation_service.load_situation_artifact(output_path)

    assert written == output_path
    assert loaded == payload


def test_run_situation_analysis_doc_flow_uses_defaults(monkeypatch, tmp_path: Path) -> None:
    doc_path = tmp_path / "cases" / "situations" / "nokia-elop-2010.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("content", encoding="utf-8")

    validated_paths: list[Path] = []
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        situation_service,
        "validate_situation_source_or_raise",
        lambda p: validated_paths.append(Path(p)),
    )
    monkeypatch.setattr(
        situation_service,
        "_resolve_actor_ref_for_analysis",
        lambda *, actor, input_path: "output/actors/nokia-elop-2010/actor_ontology.json",
    )

    def _fake_analyze(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(situation_service, "_analyze_and_save_situation", _fake_analyze)

    situation_service.run_situation_analysis(
        doc=str(doc_path),
        input_alias=None,
        url=None,
        actor=None,
        output=None,
        pack_id=None,
        pack_version="1.0.0",
    )

    assert validated_paths == [doc_path]
    assert captured["situation_file"] == doc_path
    assert captured["actor_ref"] == "output/actors/nokia-elop-2010/actor_ontology.json"
    assert captured["pack_id"] == "strategic_actor_nokia_v1"
    assert captured["pack_version"] == "1.0.0"
    assert captured["output_path"] == Path("data/scenarios/strategic_actor_nokia_v1/situation.json")


def test_run_situation_analysis_url_flow_generates_case_then_analyzes(monkeypatch, tmp_path: Path) -> None:
    source_path = tmp_path / "data" / "ingest" / "source" / "sample.txt"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    generated_case_path = tmp_path / "cases" / "situations" / "sap_case.md"

    calls: dict[str, object] = {}
    validated_paths: list[Path] = []

    monkeypatch.setattr(situation_service, "fetch_url_text", lambda url: "url text")
    monkeypatch.setattr(
        situation_service,
        "save_url_source_text",
        lambda url, text: source_path,
    )

    def _fake_save_case(*, source_text: str, source_ref: str, source_text_path: str) -> Path:
        calls["source_text"] = source_text
        calls["source_ref"] = source_ref
        calls["source_text_path"] = source_text_path
        return generated_case_path

    monkeypatch.setattr(situation_service, "save_situation_case_from_source", _fake_save_case)
    monkeypatch.setattr(
        situation_service,
        "_resolve_actor_ref_for_analysis",
        lambda *, actor, input_path: "output/actors/sap-case/actor_ontology.json",
    )
    monkeypatch.setattr(
        situation_service,
        "validate_situation_source_or_raise",
        lambda p: validated_paths.append(Path(p)),
    )

    def _fake_analyze(**kwargs: object) -> None:
        calls["analyze"] = kwargs

    monkeypatch.setattr(situation_service, "_analyze_and_save_situation", _fake_analyze)

    situation_service.run_situation_analysis(
        doc=None,
        input_alias=None,
        url="https://example.com/x",
        actor=None,
        output=None,
        pack_id=None,
        pack_version="1.0.0",
    )

    assert calls["source_text"] == "url text"
    assert calls["source_ref"] == "https://example.com/x"
    assert calls["source_text_path"] == str(source_path)
    assert validated_paths == [generated_case_path]

    analyze_kwargs = calls["analyze"]
    assert isinstance(analyze_kwargs, dict)
    assert analyze_kwargs["situation_file"] == generated_case_path
    assert analyze_kwargs["pack_id"] == "strategic_actor_sap_v1"
    assert analyze_kwargs["actor_ref"] == "output/actors/sap-case/actor_ontology.json"


def test_run_situation_analysis_accepts_explicit_actor_path(monkeypatch, tmp_path: Path) -> None:
    doc_path = tmp_path / "cases" / "situations" / "case.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("content", encoding="utf-8")

    actor_path = tmp_path / "actors" / "demo.md"
    actor_path.parent.mkdir(parents=True, exist_ok=True)
    actor_path.write_text("actor", encoding="utf-8")

    captured: dict[str, object] = {}
    monkeypatch.setattr(situation_service, "validate_situation_source_or_raise", lambda p: None)
    monkeypatch.setattr(situation_service, "_analyze_and_save_situation", lambda **kwargs: captured.update(kwargs))

    situation_service.run_situation_analysis(
        doc=str(doc_path),
        input_alias=None,
        url=None,
        actor=str(actor_path),
        output=None,
        pack_id="custom_pack",
        pack_version="1.0.0",
    )

    assert captured["actor_ref"] == str(actor_path)
    assert captured["pack_id"] == "custom_pack"


def test_run_situation_analysis_rejects_conflicting_inputs() -> None:
    with pytest.raises(ValueError, match="use either --doc or --url"):
        situation_service.run_situation_analysis(
            doc="case",
            input_alias=None,
            url="https://example.com",
            actor=None,
            output=None,
            pack_id=None,
            pack_version="1.0.0",
        )


def test_run_situation_analysis_requires_doc_or_url() -> None:
    with pytest.raises(ValueError, match="missing required argument --doc or --url"):
        situation_service.run_situation_analysis(
            doc=None,
            input_alias=None,
            url=None,
            actor=None,
            output=None,
            pack_id=None,
            pack_version="1.0.0",
        )


def test_run_situation_analysis_rejects_empty_actor_argument(tmp_path: Path) -> None:
    doc_path = tmp_path / "cases" / "situations" / "case.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="actor reference is empty"):
        situation_service.run_situation_analysis(
            doc=str(doc_path),
            input_alias=None,
            url=None,
            actor="",
            output=None,
            pack_id=None,
            pack_version="1.0.0",
        )


def test_resolve_situation_artifact_ref_prefers_existing_paths(tmp_path: Path) -> None:
    direct = tmp_path / "existing.json"
    direct.write_text("{}", encoding="utf-8")

    assert situation_service.resolve_situation_artifact_ref(direct) == direct


def test_resolve_situation_artifact_ref_pack_id_maps_to_pack_root() -> None:
    resolved = situation_service.resolve_situation_artifact_ref("sap_v1")
    assert resolved == Path("data/scenarios/sap_v1/situation.json")


def test_resolve_situation_artifact_ref_keeps_explicit_json_path() -> None:
    resolved = situation_service.resolve_situation_artifact_ref("data/scenarios/sap_v1/situation.json")
    assert resolved == Path("data/scenarios/sap_v1/situation.json")


def test_save_auxiliary_json_writes_parent_dirs(tmp_path: Path) -> None:
    output = tmp_path / "x" / "y" / "log.json"
    written = situation_service.save_auxiliary_json(output, {"ok": True})

    assert written == output
    assert output.exists()


def test_run_situation_analysis_local_first_skips_when_persona_is_usable(monkeypatch, tmp_path: Path) -> None:
    doc_path = tmp_path / "cases" / "situations" / "case.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("content", encoding="utf-8")

    actor_path = tmp_path / "output" / "actors" / "case" / "actor_ontology.json"
    actor_path.parent.mkdir(parents=True, exist_ok=True)
    actor_path.write_text("{}", encoding="utf-8")
    persona_path = actor_path.parent / "analyze_persona.json"
    persona_path.write_text(
        '{"persona_insight": {"narrative": "usable", "key_traits": [], "consistency_score": 0.8}}',
        encoding="utf-8",
    )
    output_path = tmp_path / "data" / "scenarios" / "pack" / "situation.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("{}", encoding="utf-8")

    status_path = actor_path.parent / "analyze_status.json"
    status_path.write_text('{"timeline": [{"id": "e1"}], "summary": {"ok": true}}', encoding="utf-8")

    called = {"analyze": False, "ensure_status": False}

    monkeypatch.setattr(situation_service, "validate_situation_source_or_raise", lambda p: None)
    monkeypatch.setattr(
        situation_service,
        "_resolve_actor_ref_for_analysis",
        lambda *, actor, input_path: str(actor_path),
    )
    monkeypatch.setattr(
        situation_service,
        "_analyze_and_save_situation",
        lambda **kwargs: called.__setitem__("analyze", True),
    )
    monkeypatch.setattr(
        situation_service,
        "ensure_status_artifact_for_actor_ref",
        lambda *, actor_ref: called.__setitem__("ensure_status", True),
    )

    situation_service.run_situation_analysis(
        doc=str(doc_path),
        input_alias=None,
        url=None,
        actor=None,
        output=str(output_path),
        pack_id="pack",
        pack_version="1.0.0",
        force=False,
    )

    assert called["analyze"] is False
    assert called["ensure_status"] is True


def test_run_situation_analysis_does_not_skip_when_persona_is_empty(monkeypatch, tmp_path: Path) -> None:
    doc_path = tmp_path / "cases" / "situations" / "case.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("content", encoding="utf-8")

    actor_path = tmp_path / "output" / "actors" / "case" / "actor_ontology.json"
    actor_path.parent.mkdir(parents=True, exist_ok=True)
    actor_path.write_text("{}", encoding="utf-8")
    persona_path = actor_path.parent / "analyze_persona.json"
    persona_path.write_text(
        '{"persona_insight": {"narrative": "", "key_traits": [], "consistency_score": 0.0}}',
        encoding="utf-8",
    )
    output_path = tmp_path / "data" / "scenarios" / "pack" / "situation.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("{}", encoding="utf-8")

    called = {"analyze": False, "ensure_persona": False, "ensure_status": False}

    monkeypatch.setattr(situation_service, "validate_situation_source_or_raise", lambda p: None)
    monkeypatch.setattr(
        situation_service,
        "_resolve_actor_ref_for_analysis",
        lambda *, actor, input_path: str(actor_path),
    )
    monkeypatch.setattr(
        situation_service,
        "_analyze_and_save_situation",
        lambda **kwargs: called.__setitem__("analyze", True),
    )
    monkeypatch.setattr(
        situation_service,
        "ensure_persona_artifact_for_actor_ref",
        lambda *, actor_ref, config_path: called.__setitem__("ensure_persona", True),
    )
    monkeypatch.setattr(
        situation_service,
        "ensure_status_artifact_for_actor_ref",
        lambda *, actor_ref: called.__setitem__("ensure_status", True),
    )

    situation_service.run_situation_analysis(
        doc=str(doc_path),
        input_alias=None,
        url=None,
        actor=None,
        output=str(output_path),
        pack_id="pack",
        pack_version="1.0.0",
        force=False,
    )

    assert called["analyze"] is True
    assert called["ensure_persona"] is True
    assert called["ensure_status"] is True


def test_run_situation_analysis_generates_status_when_missing(monkeypatch, tmp_path: Path) -> None:
    doc_path = tmp_path / "cases" / "situations" / "case.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("content", encoding="utf-8")

    actor_path = tmp_path / "output" / "actors" / "case" / "actor_ontology.json"
    actor_path.parent.mkdir(parents=True, exist_ok=True)
    actor_path.write_text("{}", encoding="utf-8")
    persona_path = actor_path.parent / "analyze_persona.json"
    persona_path.write_text(
        '{"persona_insight": {"narrative": "usable", "key_traits": [], "consistency_score": 0.8}}',
        encoding="utf-8",
    )
    output_path = tmp_path / "data" / "scenarios" / "pack" / "situation.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("{}", encoding="utf-8")

    called = {"analyze": False, "ensure_status": False}

    monkeypatch.setattr(situation_service, "validate_situation_source_or_raise", lambda p: None)
    monkeypatch.setattr(
        situation_service,
        "_resolve_actor_ref_for_analysis",
        lambda *, actor, input_path: str(actor_path),
    )
    monkeypatch.setattr(
        situation_service,
        "_analyze_and_save_situation",
        lambda **kwargs: called.__setitem__("analyze", True),
    )
    monkeypatch.setattr(
        situation_service,
        "ensure_status_artifact_for_actor_ref",
        lambda *, actor_ref: called.__setitem__("ensure_status", True),
    )

    situation_service.run_situation_analysis(
        doc=str(doc_path),
        input_alias=None,
        url=None,
        actor=None,
        output=str(output_path),
        pack_id="pack",
        pack_version="1.0.0",
        force=False,
    )

    assert called["analyze"] is False
    assert called["ensure_status"] is True
