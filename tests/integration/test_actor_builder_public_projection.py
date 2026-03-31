from __future__ import annotations

import json
from pathlib import Path

from omen.ingest.llm_ontology.actor_builder import extract_actor_ontology
from omen.ingest.llm_ontology.document_loader import load_case_document
from omen.ingest.models.case_models import LLMConfig


def _minimal_config() -> LLMConfig:
    return LLMConfig(
        provider="deepseek",
        base_url="https://api.example.test",
        chat_model="deepseek-chat",
        embedding_model="voyage-3-lite",
        deepseek_api_key="dummy",
        voyage_api_key="dummy",
    )


def test_actor_builder_projects_public_profile_for_fixed_chen_case(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source = repo_root / "cases" / "actors" / "chen-jiaxing.md"
    assert source.exists(), f"missing fixed case: {source}"

    case_doc = load_case_document(
        source,
        case_id="chen-jiaxing",
        title="Chen Jiaxing",
        known_outcome="unknown",
    )

    llm_payload = {
        "meta": {
            "version": "v0.1.0-actor-centric",
            "case_id": "chen-jiaxing",
            "disclosure_level": "public-structure",
            "strategic_dimensions": ["mental_patterns", "strategic_style"],
        },
        "actors": [
            {
                "id": "actor-chen-jiaxing",
                "name": "Strategic Actor",
                "type": "role",
                "profile": {
                    "background_facts": {
                        "birth_year": 1990,
                        "origin": "China",
                        "career_trajectory": ["Engineer", "Founder"],
                    },
                    "mental_patterns": {"redacted": True},
                    "strategic_style": {"redacted": True},
                },
            },
            {
                "id": "actor-x-developer-team",
                "name": "X-Developer internal team",
                "type": "role",
                "role": "internal development team",
            },
            {
                "id": "actor-pilot-customer",
                "name": "Pilot customer organization",
                "type": "role",
                "role": "customer (pilot team)",
            },
            {
                "id": "actor-tech-managers",
                "name": "Technical managers",
                "type": "role",
                "role": "target customer segment (technical leadership)",
            },
            {
                "id": "actor-developers",
                "name": "Developers",
                "type": "role",
                "role": "end-user (software engineers)",
            },
        ],
        "events": [
            {
                "id": "chen-jiaxing-1",
                "name": "launch",
                "type": "event",
                "date": "2019-10",
                "description": "X-Developer platform launched.",
                "actors_involved": ["actor-chen-jiaxing", "actor-x-developer-team"],
            }
        ],
        "influences": [],
    }

    class _Response:
        content = json.dumps(llm_payload, ensure_ascii=False)

    class _Chat:
        def invoke(self, _prompt: str):
            return _Response()

    monkeypatch.setattr("omen.ingest.llm_ontology.actor_builder.create_chat_client", lambda _cfg: _Chat())

    actor_ontology = extract_actor_ontology(
        case_doc=case_doc,
        chunks=[case_doc.raw_text[:2000]],
        config=_minimal_config(),
        timeline_events=[
            {
                "id": "chen-jiaxing-1",
                "event": "launch",
                "description": "X-Developer platform launched.",
                "time": "2019-10",
            }
        ],
    )

    assert actor_ontology["meta"] == {
        "version": "v0.1.0-actor",
        "case_id": "chen-jiaxing",
    }

    actors = actor_ontology["actors"]
    assert len(actors) >= 5

    primary = next(actor for actor in actors if actor["id"] == "actor-chen-jiaxing")
    assert primary["type"] == "StrategicActor"
    assert primary["name"] == "Chen Jiaxing"
    assert primary["role"] == "founder"
    assert primary["profile"] == {
        "background_facts": {
            "birth_year": 1990,
            "origin": "China",
            "education": [],
            "career_trajectory": ["Engineer", "Founder"],
            "key_experiences": [],
        }
    }
    assert "mental_patterns" not in primary["profile"]
    assert "strategic_style" not in primary["profile"]

    actor_ids = {actor["id"] for actor in actors}
    assert "actor-x-developer-team" in actor_ids
    assert "actor-pilot-customer" in actor_ids

    by_id = {actor["id"]: actor for actor in actors}
    assert by_id["actor-pilot-customer"]["role"] == "customer"
    assert by_id["actor-tech-managers"]["role"] == "target customer segment"
    assert by_id["actor-developers"]["role"] == "end-user"
