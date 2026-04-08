"""Markdown report renderers in workflows."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from omen.ingest.synthesizer.clients import invoke_text_prompt, render_prompt_template
from omen.ingest.synthesizer.prompts.registry import get_prompt_template

_REQUIRED_SECTION_LABELS = (
    "strategic situation brief",
    "current state",
    "target outcomes",
    "core question",
    "dilemma",
    "key decision point",
    "hard constraints",
    "known unknowns",
    "confidence & uncertainty",
    "omen reminder",
)


def _slugify_case_name(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value).strip())
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_") or "situation_case"


def _normalize_text_lines(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []

    output: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            output.append(text)
    return output


def _normalize_direct_quotes(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    output: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        speaker = str(item.get("speaker_role") or "").strip()
        quote = str(item.get("quote") or "").strip()
        if speaker and quote:
            output.append({"speaker_role": speaker, "quote": quote})
    return output


def _render_case_template(template_text: str, values: dict[str, str]) -> str:
    rendered = template_text
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _as_bullet_block(items: list[str], *, fallback: str) -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def _as_quote_block(items: list[str], *, fallback: str) -> str:
    if not items:
        return f"> {fallback}"

    paragraphs: list[str] = []
    for item in items:
        lines = [line.strip() for line in item.splitlines() if line.strip()]
        if not lines:
            continue
        paragraphs.append("\n".join(f"> {line}" for line in lines))

    if not paragraphs:
        return f"> {fallback}"
    return "\n\n".join(paragraphs)


def _load_brief_template() -> str:
    template_path = Path("config/templates/situation_brief.md")
    return template_path.read_text(encoding="utf-8")


def _load_report_prompts() -> tuple[str, str]:
    system_prompt = get_prompt_template("report_system_prompt", tier="report")
    user_prompt = get_prompt_template("situation_brief_user_prompt", tier="report")
    return system_prompt, user_prompt


def _looks_like_expected_brief(markdown: str) -> bool:
    text = markdown.strip()
    if not text:
        return False
    lowered = text.lower()
    return all(label in lowered for label in _REQUIRED_SECTION_LABELS)


def _build_brief_prompt_payload(situation: dict[str, Any]) -> dict[str, Any]:
    context = dict(situation.get("context") or {})
    source_meta = dict(situation.get("source_meta") or {})
    uncertainty_space = dict(situation.get("uncertainty_space") or {})

    return {
        "id": situation.get("id"),
        "version": situation.get("version"),
        "core_topic": context.get("title"),
        "source_path": source_meta.get("source_path"),
        "generated_at": source_meta.get("generated_at"),
        "context": {
            "title": context.get("title"),
            "core_question": context.get("core_question"),
            "current_state": context.get("current_state"),
            "core_dilemma": context.get("core_dilemma"),
            "key_decision_point": context.get("key_decision_point"),
            "target_outcomes": list(context.get("target_outcomes") or []),
            "hard_constraints": list(context.get("hard_constraints") or []),
            "known_unknowns": list(context.get("known_unknowns") or []),
        },
        "brief_confidence": {
            "risk_confidence": uncertainty_space.get("confidence_risk"),
            "known_unknowns": list(context.get("known_unknowns") or []),
        },
    }


def render_situation_brief(situation: dict[str, object], config_path: str = "config/llm.toml") -> str:
    template = _load_brief_template()
    system_prompt, user_prompt_template = _load_report_prompts()
    prompt_payload = _build_brief_prompt_payload(dict(situation))

    user_prompt = render_prompt_template(
        user_prompt_template,
        {
            "format_template": template,
            "situation_json": json.dumps(prompt_payload, ensure_ascii=False, indent=2),
        },
    )
    generated = invoke_text_prompt(
        config_path=config_path,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    if not _looks_like_expected_brief(generated):
        raise ValueError("generated situation brief does not match expected report format")
    return generated.strip() + "\n"


def render_situation_case(
    *,
    payload: dict[str, Any],
    source_ref: str,
    source_text_path: str,
    capture_date: str | None = None,
) -> tuple[str, str]:
    template_path = Path("config/templates/situation_case.md")
    template_text = template_path.read_text(encoding="utf-8")

    case_name = _slugify_case_name(str(payload.get("case_name") or "situation_case"))
    event_title = str(payload.get("event_title") or case_name.replace("_", " ").title()).strip()
    event_date = str(payload.get("event_date_or_announcement_date") or "announcement date").strip()
    context = str(payload.get("context") or "No direct context statement extracted from source.").strip()
    story = str(payload.get("story") or payload.get("narrative") or "No story fragment extracted from source.").strip()

    direct_quotes = _normalize_direct_quotes(payload.get("direct_quotes"))
    direct_quote_lines = [f'{item["speaker_role"]}: "{item["quote"]}"' for item in direct_quotes]

    markdown = _render_case_template(
        template_text,
        {
            "event_title": event_title,
            "source_url": source_ref,
            "capture_date": capture_date or datetime.now().date().isoformat(),
            "event_date_or_announcement_date": event_date,
            "source_text_path": source_text_path,
            "context": context,
            "core_facts": _as_bullet_block(
                _normalize_text_lines(payload.get("core_facts")),
                fallback="No direct core fact extracted from source.",
            ),
            "data_findings": _as_bullet_block(
                _normalize_text_lines(payload.get("data_findings")),
                fallback="No explicit quantitative finding extracted from source.",
            ),
            "raw_context": _as_bullet_block(
                _normalize_text_lines(payload.get("raw_context")),
                fallback="No additional raw context extracted from source.",
            ),
            "story": story,
            "direct_quotes": _as_bullet_block(
                direct_quote_lines,
                fallback="No direct quote extracted from source.",
            ),
            "difficulties_risks_controversies": _as_bullet_block(
                _normalize_text_lines(
                    payload.get("difficulties_risks_controversies")
                    or payload.get("risks")
                ),
                fallback="No explicit difficulty, risk, or controversy extracted from source.",
            ),
            "unknowns": _as_bullet_block(
                _normalize_text_lines(payload.get("unknowns")),
                fallback="No explicit unknown extracted from source.",
            ),
            "representative_excerpt": _as_quote_block(
                _normalize_text_lines(payload.get("representative_excerpt")),
                fallback="No representative long-form excerpt extracted from source.",
            ),
        },
    ).strip()

    return case_name, markdown + "\n"
