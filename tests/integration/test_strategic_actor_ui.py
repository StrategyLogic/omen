from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
from types import SimpleNamespace


def _load_ui_module():
    if "streamlit" not in sys.modules:
        fake = types.ModuleType("streamlit")

        def _noop(*_: object, **__: object) -> None:
            return None

        fake.set_page_config = _noop
        fake.title = _noop
        fake.caption = _noop
        fake.warning = _noop
        fake.error = _noop
        fake.header = _noop
        fake.subheader = _noop
        fake.info = _noop
        fake.markdown = _noop
        fake.write = _noop
        fake.plotly_chart = _noop
        fake.json = _noop
        fake.columns = lambda *_: []
        fake.sidebar = types.SimpleNamespace(selectbox=lambda *_: "", text_input=lambda *_: "output/actors")
        fake.expander = lambda *_: types.SimpleNamespace(__enter__=lambda self: self, __exit__=lambda *a: False)
        sys.modules["streamlit"] = fake

    module_path = Path(__file__).resolve().parents[2] / "app" / "strategic_actor.py"
    spec = importlib.util.spec_from_file_location("strategic_actor_app", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_strategic_actor_ui_timeline_rows_extraction() -> None:
    module = _load_ui_module()
    rows = module.extract_timeline_rows(
        {
            "timeline": [
                {"id": "e1", "time": "2016", "name": "launch", "description": "launch desc"},
            ]
        }
    )
    assert len(rows) == 1
    assert rows[0]["id"] == "e1"
    assert rows[0]["description"] == "launch desc"


def test_strategic_actor_ui_lists_cases_from_cases_actors(tmp_path: Path, monkeypatch) -> None:
    module = _load_ui_module()
    cases_dir = tmp_path / "cases" / "actors"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / "zeta.md").write_text("z", encoding="utf-8")
    (cases_dir / "alpha.md").write_text("a", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    assert module._list_actor_case_ids() == ["alpha", "zeta"]
    assert module._suggest_actor_document_path("alpha").endswith("cases/actors/alpha.md")


def test_actor_pipeline_passes_output_language_to_persona(tmp_path: Path, monkeypatch) -> None:
    module = _load_ui_module()

    target_case_dir = tmp_path / "output" / "actors" / "alpha"
    target_case_dir.mkdir(parents=True, exist_ok=True)

    captured: dict[str, str] = {}

    monkeypatch.setattr(module, "ensure_actor_output_dir", lambda *_args, **_kwargs: target_case_dir)
    monkeypatch.setattr(
        module,
        "generate_strategy_ontology_from_document",
        lambda **_kwargs: SimpleNamespace(
            strategy_ontology={"meta": {"case_id": "alpha"}, "abox": {}},
            inferred_known_outcome=None,
            validation_passed=True,
            validation_issues=[],
        ),
    )
    monkeypatch.setattr(
        module,
        "generate_actor_and_events_from_document",
        lambda **_kwargs: (
            {
                "meta": {"case_id": "alpha", "version": "1.0.0"},
                "actors": [{"id": "a1", "shared_id": "a1"}],
                "events": [{"id": "e1", "event": "launch", "time": "2016"}],
                "query_skeleton": {"query_types": ["status", "persona"]},
            },
            [{"id": "e1", "event": "launch", "description": "launch", "time": "2016"}],
        ),
    )
    monkeypatch.setattr(module, "attach_timeline_events", lambda payload, _timeline: payload)
    monkeypatch.setattr(module, "attach_actor_ref", lambda payload, _actor, **_kwargs: payload)
    monkeypatch.setattr(
        module,
        "save_strategy_ontology",
        lambda payload, path: path.write_text(__import__("json").dumps(payload), encoding="utf-8") or path,
    )
    monkeypatch.setattr(module, "build_status_snapshot", lambda **_kwargs: {"timeline": []})

    def _fake_persona(**kwargs):
        captured["output_language"] = str(kwargs.get("output_language"))
        return {"persona_insight": {"narrative": "n", "key_traits": ["t1"]}}

    monkeypatch.setattr(module, "generate_persona_insight", _fake_persona)

    module._run_actor_pipeline(
        case_id="alpha",
        title="Alpha",
        document_path=str(tmp_path / "cases" / "actors" / "alpha.md"),
        known_outcome="unknown",
        config_path="config/llm.toml",
        status_date="",
        output_root=str(tmp_path / "output" / "actors"),
        output_language="zh",
    )

    assert captured["output_language"] == "zh"


def test_strategic_actor_ui_has_start_and_retry_button_copy() -> None:
    module = _load_ui_module()

    # Guard CTA button copy used by the UI trigger against accidental regressions.
    assert module.UI_TEXT["zh"]["cta_start"] == "开始分析"
    assert module.UI_TEXT["zh"]["cta_again"] == "重新分析"
    assert module.UI_TEXT["en"]["cta_start"] == "Start Analysis"
    assert module.UI_TEXT["en"]["cta_again"] == "Analysis Again"
