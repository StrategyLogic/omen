"""Prompt registry for open/pro template routing."""

from __future__ import annotations

from dataclasses import dataclass

from omen.ingest.llm_ontology.prompt_loader import get_prompt_file_path, load_tier_prompts


@dataclass(frozen=True)
class AnalyzePromptBinding:
    command: str
    tier: str
    template_key: str


ANALYZE_PROMPT_BINDINGS: dict[str, AnalyzePromptBinding] = {
    "persona": AnalyzePromptBinding(command="persona", tier="base", template_key="persona_insight"),
    "why": AnalyzePromptBinding(command="why", tier="pro", template_key="founder_why"),
    "formation": AnalyzePromptBinding(command="formation", tier="pro", template_key="strategic_formation"),
    "insight": AnalyzePromptBinding(command="insight", tier="pro", template_key="founder_gap"),
}


def get_prompt_template(template_key: str, *, tier: str) -> str:
    prompts = load_tier_prompts(tier)
    try:
        return prompts[template_key]
    except KeyError as exc:
        prompt_path = get_prompt_file_path(tier)
        raise KeyError(f"prompt template `{template_key}` not found in {prompt_path}") from exc


def get_prompt_template_or_default(template_key: str, *, tier: str, default: str) -> str:
    try:
        return get_prompt_template(template_key, tier=tier)
    except (FileNotFoundError, KeyError, ValueError):
        return default.strip()


def resolve_analyze_prompt_binding(command: str) -> AnalyzePromptBinding:
    normalized = str(command).strip().lower()
    try:
        return ANALYZE_PROMPT_BINDINGS[normalized]
    except KeyError as exc:
        raise KeyError(f"unsupported analyze prompt command: {command}") from exc


def ensure_analyze_prompt_available(command: str) -> AnalyzePromptBinding:
    binding = resolve_analyze_prompt_binding(command)
    get_prompt_template(binding.template_key, tier=binding.tier)
    return binding
