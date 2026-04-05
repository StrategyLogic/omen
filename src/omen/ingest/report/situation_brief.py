"""Template-based renderer for Situation markdown brief."""

from __future__ import annotations

import json
from pathlib import Path

from omen.ingest.llm_ontology.clients import invoke_text_prompt, render_prompt_template
from omen.ingest.llm_ontology.prompts.registry import get_prompt_template

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
def _load_template() -> str:
    template_path = Path(__file__).resolve().parent / "templates" / "situation_brief.md"
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


def render_situation_brief(situation: dict[str, object]) -> str:
    template = _load_template()
    system_prompt, user_prompt_template = _load_report_prompts()

    user_prompt = render_prompt_template(
        user_prompt_template,
        {
            "format_template": template,
            "situation_json": json.dumps(situation, ensure_ascii=False, indent=2),
        },
    )
    generated = invoke_text_prompt(
        config_path="config/llm.toml",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    if not _looks_like_expected_brief(generated):
        raise ValueError("generated situation brief does not match expected report format")
    return generated.strip() + "\n"
