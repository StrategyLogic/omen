"""Prompt registry for open/pro template routing."""

from __future__ import annotations

from dataclasses import dataclass

from omen.ingest.synthesizer.prompts.loader import (
    get_prompt_file_path,
    load_tier_prompt_meta,
    load_tier_prompts,
)


@dataclass(frozen=True)
class AnalyzePromptBinding:
    command: str
    tier: str
    template_key: str


@dataclass(frozen=True)
class PromptMetadata:
    template_key: str
    tier: str
    prompt_id: str
    version: str

    @property
    def token(self) -> str:
        pid = self.prompt_id or f"{self.tier}.{self.template_key}"
        ver = self.version or "unknown"
        return f"{pid}@{ver}"


ANALYZE_PROMPT_BINDINGS: dict[str, AnalyzePromptBinding] = {
    "persona": AnalyzePromptBinding(command="persona", tier="base", template_key="persona_insight"),
}


def get_prompt_template(template_key: str, *, tier: str) -> str:
    prompts = load_tier_prompts(tier)
    try:
        return prompts[template_key]
    except KeyError as exc:
        prompt_path = get_prompt_file_path(tier)
        raise KeyError(f"prompt template `{template_key}` not found in {prompt_path}") from exc


def get_prompt_metadata(template_key: str, *, tier: str) -> PromptMetadata:
    meta_map = load_tier_prompt_meta(tier)
    meta = meta_map.get(template_key) or {}
    return PromptMetadata(
        template_key=template_key,
        tier=tier,
        prompt_id=str(meta.get("id") or "").strip(),
        version=str(meta.get("version") or "").strip(),
    )


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


def get_analyze_prompt_version_token(command: str) -> str:
    binding = resolve_analyze_prompt_binding(command)
    metadata = get_prompt_metadata(binding.template_key, tier=binding.tier)
    return metadata.token


def get_scenario_reason_chain_prompt_version_token() -> str:
    metadata = get_prompt_metadata("scenario_reason_chain_prompt", tier="base")
    return metadata.token


def get_action_suggestion_prompt_version_token() -> str:
    metadata = get_prompt_metadata("action_suggestion_prompt", tier="base")
    return metadata.token
