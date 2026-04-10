from __future__ import annotations

from pathlib import Path

from omen.ingest.synthesizer.builders.actor import extract_actor_ontology
from omen.ingest.processor import load_case_document
from omen.ingest.models import LLMConfig


def _minimal_config() -> LLMConfig:
    return LLMConfig(
        provider="deepseek",
        base_url="https://api.example.test",
        chat_model="deepseek-chat",
        embedding_model="voyage-3-lite",
        deepseek_api_key="dummy",
        voyage_api_key="dummy",
    )


def test_actor_builder_profile_for_chen_case(monkeypatch) -> None:
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
                    "strategic_style": {
                        "decision_style": "data-driven",
                        "value_proposition": "replace process tools",
                        "decision_preferences": ["automation first"],
                        "non_negotiables": ["no manual input"],
                    },
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
                "profile": {
                    "interest": "Validate delivery outcomes",
                    "influence_level": "medium",
                    "alignment_with_strategic_actor": "high",
                },
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

    monkeypatch.setattr(
        "omen.ingest.synthesizer.builders.actor.invoke_json_prompt",
        lambda **kwargs: llm_payload,
    )

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

    assert "constraints" not in actor_ontology

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
        },
        "strategic_style": {
            "decision_style": "data-driven",
            "value_proposition": "replace process tools",
            "decision_preferences": ["automation first"],
            "non_negotiables": ["no manual input"],
        },
    }
    assert "mental_patterns" not in primary["profile"]

    actor_ids = {actor["id"] for actor in actors}
    assert "actor-x-developer-team" in actor_ids
    assert "actor-pilot-customer" in actor_ids

    by_id = {actor["id"]: actor for actor in actors}
    assert by_id["actor-pilot-customer"]["role"] == "customer"
    assert by_id["actor-pilot-customer"]["profile"] == {
        "interest": "Validate delivery outcomes",
        "influence_level": "medium",
        "alignment_with_strategic_actor": "high",
    }
    assert by_id["actor-tech-managers"]["role"] == "target customer segment"
    assert by_id["actor-developers"]["role"] == "end-user"


def test_actor_builder_normalizes_competitor_product_and_influences(monkeypatch) -> None:
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
        "meta": {"version": "v0.1.0-actor", "case_id": "chen-jiaxing"},
        "actors": [
            {
                "id": "actor-founder-1",
                "name": "Chen Jiaxing",
                "type": "founder",
                "profile": {
                    "birth_year": "1989",
                    "origin": "China",
                },
            },
            {
                "id": "actor-competitor-process-tools",
                "name": "Project Management / Collaboration Tools",
                "type": "actor",
                "role": "competitor",
            },
        ],
        "products": [
            {
                "id": "product-x-developer",
                "name": "X-Developer",
                "type": "platform",
            }
        ],
        "events": [],
        "influences": [],
    }

    monkeypatch.setattr(
        "omen.ingest.synthesizer.builders.actor.invoke_json_prompt",
        lambda **kwargs: llm_payload,
    )

    actor_ontology = extract_actor_ontology(
        case_doc=case_doc,
        chunks=[case_doc.raw_text[:2000]],
        config=_minimal_config(),
        timeline_events=[],
    )

    founder = next(actor for actor in actor_ontology["actors"] if actor["id"] == "actor-founder-1")
    assert founder["profile"]["background_facts"]["birth_year"] == 1989
    assert founder["profile"]["background_facts"]["origin"] == "China"
    assert founder["profile"]["strategic_style"] == {
        "decision_style": None,
        "value_proposition": None,
        "decision_preferences": [],
        "non_negotiables": [],
    }

    products_by_id = {item["id"]: item for item in actor_ontology["products"]}
    assert "competitor-process-tools" in products_by_id
    assert products_by_id["competitor-process-tools"]["type"] == "competitor"

    influence_keys = {
        (edge["source"], edge["target"], edge["type"])
        for edge in actor_ontology["influences"]
    }
    assert ("competitor-process-tools", "actor-founder-1", "influences") in influence_keys
    assert ("actor-founder-1", "competitor-process-tools", "builds") not in influence_keys


def test_actor_builder_backfills_background_facts_from_events(monkeypatch) -> None:
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
        "meta": {"version": "v0.1.0-actor", "case_id": "chen-jiaxing"},
        "actors": [
            {
                "id": "actor-founder-1",
                "name": "Chen Jiaxing",
                "type": "founder",
                "profile": {
                    "background_facts": {
                        "birth_year": None,
                        "origin": None,
                        "education": [],
                        "career_trajectory": [],
                        "key_experiences": [],
                    }
                },
            }
        ],
        "events": [
            {
                "id": "event-launch",
                "name": "Platform Launch",
                "description": "X-Developer platform launched after validation.",
                "date": "2019-10",
                "actors_involved": ["actor-founder-1"],
            }
        ],
        "influences": [],
    }

    monkeypatch.setattr(
        "omen.ingest.synthesizer.builders.actor.invoke_json_prompt",
        lambda **kwargs: llm_payload,
    )

    actor_ontology = extract_actor_ontology(
        case_doc=case_doc,
        chunks=[case_doc.raw_text[:2000]],
        config=_minimal_config(),
        timeline_events=[],
    )

    founder = actor_ontology["actors"][0]
    assert founder["profile"]["background_facts"]["key_experiences"] == [
        "X-Developer platform launched after validation."
    ]
