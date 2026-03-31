from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

from omen.analysis.actor.query import build_events_snapshot


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


def test_timeline_description_fallback_priority() -> None:
    module = _load_ui_module()
    rows = module.extract_timeline_rows(
        {
            "timeline": [
                {"id": "e1", "time": "2016", "event": "launch", "summary": "from summary"},
                {"id": "e2", "time": "2017", "event": "pilot", "event_excerpt": "from excerpt"},
            ]
        }
    )

    assert rows[0]["description"] == "from summary"
    assert rows[1]["description"] == "from excerpt"


def test_timeline_empty_state_returns_empty_rows() -> None:
    module = _load_ui_module()
    assert module.extract_timeline_rows({"timeline": []}) == []
    assert module.extract_timeline_rows({}) == []


def test_actor_graph_uses_strategic_actor_and_role_labels() -> None:
    payload = build_events_snapshot(
        strategy_ontology={"abox": {}},
        actor_ontology={
            "meta": {"case_id": "xd"},
            "actors": [
                {
                    "id": "a1",
                    "name": "Leader",
                    "type": "StrategicActor",
                    "role": "founder",
                    "profile": {"mental_patterns": {}, "strategic_style": {}},
                },
                {"id": "a2", "name": "Buyer", "type": "Actor", "role": "customer"},
            ],
            "events": [{"id": "e1", "name": "Launch", "date": "2016", "actors_involved": ["a1", "a2"]}],
            "influences": [],
        },
    )

    nodes = payload["actor_graph"]["nodes"]
    by_id = {node["id"]: node for node in nodes}
    assert by_id["a1"]["node_type"] == "strategic_actor"
    assert by_id["a1"]["label"].endswith("(Strategic Actor)")
    assert by_id["a2"]["node_type"] == "customer"
    assert by_id["a2"]["label"].endswith("(customer)")
