import json

from omen.ingest.llm_ontology.event_builder import extract_timeline_events
from omen.ingest.llm_ontology.founder_actor_enhancer import enhance_actor_decision_relationships
from omen.ingest.llm_ontology.founder_builder import extract_founder_ontology
from omen.ingest.llm_ontology.strategy_assembler import attach_founder_ref, attach_timeline_events
from omen.models.case_replay_models import CaseDocument, LLMConfig


def _dummy_config() -> LLMConfig:
    return LLMConfig(
        base_url="https://example.com",
        chat_model="dummy-chat",
        embedding_model="dummy-embed",
        deepseek_api_key="x",
        voyage_api_key="y",
    )


def _dummy_case() -> CaseDocument:
    return CaseDocument(
        case_id="xd",
        title="X Developer",
        content_type="markdown",
        source_path="cases/x-developer.md",
        raw_text="2016 founder made a pivot decision under capital pressure",
        known_outcome="pivoted",
    )


def test_event_and_founder_extractors_fallback_without_llm(monkeypatch):
    from omen.ingest.llm_ontology import event_builder, founder_builder

    def _raise(_config):
        raise RuntimeError("offline")

    monkeypatch.setattr(event_builder, "create_chat_client", _raise)
    monkeypatch.setattr(founder_builder, "create_chat_client", _raise)

    case_doc = _dummy_case()
    config = _dummy_config()
    chunks = [case_doc.raw_text]

    events = extract_timeline_events(case_doc=case_doc, chunks=chunks, config=config)
    assert len(events) >= 1
    assert "time" in events[0]
    assert "event" in events[0]
    assert "description" in events[0]
    assert events[0]["event"] in {"launch", "release", "pilot", "pricing", "expansion", "other"}

    founder = extract_founder_ontology(
        case_doc=case_doc,
        chunks=chunks,
        config=config,
        timeline_events=events,
    )
    assert founder["meta"]["case_id"] == "xd"
    assert founder["query_skeleton"]["query_types"] == ["status", "why", "persona"]


def test_strategy_assembler_attaches_events_and_founder_ref():
    strategy = {"meta": {"case_id": "xd", "version": "1.0.0"}, "abox": {}}
    founder = {
        "meta": {"version": "1.0.0", "case_id": "xd"},
        "actors": [{"id": "founder.xd", "shared_id": "actor:founder:xd"}],
    }
    events = [
        {
            "id": "event.1",
            "time": "2016",
            "event": "pilot",
            "description": "10-person pilot completed in three weeks",
            "evidence_refs": ["doc:1"],
        }
    ]

    merged = attach_timeline_events(strategy, events)
    merged = attach_founder_ref(merged, founder, founder_filename="founder_ontology.json")

    assert merged["abox"]["events"][0]["event_id"] == "event.1"
    assert merged["abox"]["events"][0]["event"] == "pilot"
    assert merged["abox"]["events"][0]["description"] == "10-person pilot completed in three weeks"
    assert merged["founder_ref"]["path"] == "founder_ontology.json"
    assert merged["founder_ref"]["identity_map"]["actor:founder:xd"] == "founder.xd"


def test_enhance_actor_decision_relationships_excludes_founder_actor(monkeypatch):
    from omen.ingest.llm_ontology import founder_actor_enhancer

    class _DummyResponse:
        def __init__(self, content: str) -> None:
            self.content = content

    class _DummyChat:
        def invoke(self, _prompt: str) -> _DummyResponse:
            return _DummyResponse(
                json.dumps(
                    [
                        {
                            "source": "actor-software-teams",
                            "target": "actor-tech-managers",
                            "type": "co_decision_alignment",
                            "description": "shared decision context",
                        }
                    ],
                    ensure_ascii=False,
                )
            )

    monkeypatch.setattr(founder_actor_enhancer, "create_chat_client", lambda _config: _DummyChat())

    founder_ontology = {
        "meta": {"case_id": "x-developer"},
        "actors": [
            {"id": "founder.xd", "name": "Founder", "role": "founder"},
            {"id": "actor-tech-managers", "name": "Technical Managers", "type": "role"},
            {"id": "actor-software-teams", "name": "Software Teams", "type": "role"},
        ],
        "events": [
            {
                "id": "xdev-3",
                "label": "pilot",
                "actors_involved": ["founder.xd", "actor-tech-managers", "actor-software-teams"],
                "evidence_refs": ["doc:pilot"],
            }
        ],
        "constraints": [
            {
                "id": "constraint-1",
                "type": "value_proposition",
                "applies_to": ["actor-tech-managers", "actor-software-teams"],
            }
        ],
        "influences": [],
    }

    enhanced, added = enhance_actor_decision_relationships(founder_ontology, config=_dummy_config())

    assert added >= 1
    influences = enhanced["influences"]
    assert any(
        rel.get("source") == "actor-software-teams"
        and rel.get("target") == "actor-tech-managers"
        and rel.get("type") in {"co_decision_alignment", "shared_constraint_context"}
        for rel in influences
    )
    assert not any(rel.get("source") == "founder.xd" or rel.get("target") == "founder.xd" for rel in influences)


def test_enhance_actor_decision_relationships_infers_company_as_founder_when_missing_flag(monkeypatch):
    from omen.ingest.llm_ontology import founder_actor_enhancer

    class _DummyResponse:
        def __init__(self, content: str) -> None:
            self.content = content

    class _DummyChat:
        def invoke(self, _prompt: str) -> _DummyResponse:
            return _DummyResponse(
                json.dumps(
                    [
                        {
                            "source": "actor-customer",
                            "target": "actor-manager",
                            "type": "co_decision_alignment",
                            "description": "pilot collaboration",
                        },
                        {
                            "source": "actor-xdev-team",
                            "target": "actor-customer",
                            "type": "co_decision_alignment",
                            "description": "should be filtered because founder inferred",
                        },
                    ],
                    ensure_ascii=False,
                )
            )

    monkeypatch.setattr(founder_actor_enhancer, "create_chat_client", lambda _config: _DummyChat())

    founder_ontology = {
        "meta": {"case_id": "x-developer"},
        "actors": [
            {"id": "actor-xdev-team", "name": "X-Developer Team", "type": "company"},
            {"id": "actor-customer", "name": "Customer Team", "type": "customer"},
            {"id": "actor-manager", "name": "Technical Managers", "type": "role"},
        ],
        "events": [
            {
                "id": "xdev-3",
                "label": "pilot",
                "actors_involved": ["actor-xdev-team", "actor-customer", "actor-manager"],
                "evidence_refs": ["doc:pilot"],
            }
        ],
        "constraints": [],
        "influences": [],
    }

    enhanced, _ = enhance_actor_decision_relationships(founder_ontology, config=_dummy_config())
    influences = enhanced["influences"]

    assert any(
        rel.get("source") == "actor-customer"
        and rel.get("target") == "actor-manager"
        and rel.get("type") == "co_decision_alignment"
        for rel in influences
    )
    assert not any(
        rel.get("source") == "actor-xdev-team" or rel.get("target") == "actor-xdev-team"
        for rel in influences
    )


def test_extract_founder_ontology_moves_product_like_actor_to_products(monkeypatch):
    from omen.ingest.llm_ontology import founder_builder

    class _DummyResponse:
        def __init__(self, content: str) -> None:
            self.content = content

    class _DummyChat:
        def invoke(self, _prompt: str) -> _DummyResponse:
            payload = {
                "meta": {"case_id": "xd", "slice": "founder", "version": "1.0", "generated_at": "now"},
                "actors": [
                    {"id": "actor-xdev", "name": "X-Developer Platform", "type": "product"},
                    {"id": "actor-founder", "name": "Founder Team", "type": "company"},
                ],
                "events": [],
                "constraints": [],
                "influences": [],
                "query_skeleton": {},
            }
            return _DummyResponse(json.dumps(payload, ensure_ascii=False))

    monkeypatch.setattr(founder_builder, "create_chat_client", lambda _config: _DummyChat())

    founder = extract_founder_ontology(
        case_doc=_dummy_case(),
        chunks=[_dummy_case().raw_text],
        config=_dummy_config(),
        timeline_events=[],
    )

    actor_types = {str(item.get("type") or "") for item in founder.get("actors") or [] if isinstance(item, dict)}
    assert "product" not in actor_types
    assert any(item.get("id") == "actor-xdev" for item in founder.get("products") or [])
    assert any(
        item.get("source") == "actor-founder"
        and item.get("target") == "actor-xdev"
        and item.get("type") == "builds"
        for item in founder.get("influences") or []
    )
