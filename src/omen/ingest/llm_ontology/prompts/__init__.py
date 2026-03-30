"""Prompt builders for Spec 6 document-to-ontology generation."""

from __future__ import annotations

from omen.ingest.llm_ontology.prompt_registry import get_prompt_template
from omen.models.case_replay_models import CaseDocument


def _render_template(template: str, values: dict[str, object]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"[[{key}]]", str(value))
    return rendered.strip()


def build_system_prompt() -> str:
    return get_prompt_template("system_prompt", tier="base").strip()


def build_user_prompt(
    doc: CaseDocument,
    chunks: list[str],
    strategy: str | None = None,
) -> str:
    chunk_text = "\n\n---\n\n".join(chunks)
    preferred_strategy = strategy or "infer from the case evidence"
    template = get_prompt_template("user_prompt", tier="base")
    return _render_template(
        template,
        {
            "case_id": doc.case_id,
            "title": doc.title,
            "known_outcome": doc.known_outcome,
            "source_path": doc.source_path,
            "preferred_strategy": preferred_strategy,
            "chunk_text": chunk_text,
        },
    )


def build_timeline_events_prompt(doc: CaseDocument, excerpt: str) -> str:
    template = get_prompt_template("timeline_events_prompt", tier="base")
    return _render_template(
        template,
        {
            "case_id": doc.case_id,
            "title": doc.title,
            "known_outcome": doc.known_outcome,
            "excerpt": excerpt,
        },
    )


def build_actor_ontology_prompt(
    doc: CaseDocument,
    excerpt: str,
    timeline_json: str,
) -> str:
    template = get_prompt_template("actor_ontology_prompt", tier="base")
    return _render_template(
        template,
        {
            "case_id": doc.case_id,
            "title": doc.title,
            "known_outcome": doc.known_outcome,
            "timeline_json": timeline_json,
            "excerpt": excerpt,
        },
    )


def build_actor_semantic_enhancement_prompt(actor_payload_json: str, existing_relations_json: str) -> str:
    template = get_prompt_template("actor_semantic_enhancement_prompt", tier="base")
    return _render_template(
        template,
        {
            "actor_payload_json": actor_payload_json,
            "existing_relations_json": existing_relations_json,
        },
    )


def build_strategic_formation_prompt() -> str:
    return get_prompt_template("strategic_formation", tier="pro").strip()


def build_persona_insight_prompt() -> str:
    return get_prompt_template("persona_insight", tier="base").strip()


def build_founder_why_prompt() -> str:
    return get_prompt_template("founder_why", tier="pro").strip()


def build_founder_gap_prompt() -> str:
    return get_prompt_template("founder_gap", tier="pro").strip()


def build_json_retry_prompt(base_prompt: str) -> str:
    template = get_prompt_template("json_retry_prompt", tier="base")
    return _render_template(template, {"base_prompt": base_prompt})
