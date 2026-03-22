from omen.ingest.llm_ontology.event_builder import extract_timeline_events
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
