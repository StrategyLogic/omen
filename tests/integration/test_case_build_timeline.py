from __future__ import annotations

from pathlib import Path

from omen.ingest.llm_ontology.builders.event import extract_timeline_events
from omen.ingest.models import CaseDocument, LLMConfig


def _minimal_config() -> LLMConfig:
    return LLMConfig(
        provider="deepseek",
        base_url="https://api.example.test",
        chat_model="deepseek-chat",
        embedding_model="voyage-3-lite",
        deepseek_api_key="dummy",
        voyage_api_key="dummy",
    )


def test_timeline_extraction_falls_back_to_chunk_grounded_events(monkeypatch, tmp_path: Path) -> None:
    case_doc = CaseDocument(
        case_id="xd",
        title="X-Developer Replay",
        content_type="markdown",
        source_path=str(tmp_path / "case.md"),
        raw_text="The team launched a workflow platform and iterated with pilots.",
        known_outcome="gradual adoption",
    )
    chunks = [
        "2016: Product launched to early design partners.",
        "2017: Pilot phase revealed onboarding bottlenecks.",
        "2018: Pricing and expansion adjustments followed.",
    ]

    class _BrokenResponse:
        content = "not json"

    class _BrokenChatClient:
        def invoke(self, _prompt: str):
            return _BrokenResponse()

    monkeypatch.setattr(
        "omen.ingest.llm_ontology.builders.event.create_chat_client",
        lambda _cfg: _BrokenChatClient(),
    )

    events = extract_timeline_events(case_doc=case_doc, chunks=chunks, config=_minimal_config())

    assert len(events) == len(chunks)
    assert events[0]["id"] == "event.1"
    assert events[0]["evidence_refs"] == ["chunk:1"]
    assert all("description" in event for event in events)
