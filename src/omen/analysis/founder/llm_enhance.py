"""LLM-enhanced founder analysis placeholders."""

from __future__ import annotations

from typing import Any


def build_persona_prompt_payload(founder_ontology: dict[str, Any], question: str) -> dict[str, Any]:
    return {
        "question": question,
        "query_skeleton": founder_ontology.get("query_skeleton") or {},
        "actors": founder_ontology.get("actors") or [],
        "events": founder_ontology.get("events") or [],
        "constraints": founder_ontology.get("constraints") or [],
    }
