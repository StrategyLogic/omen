from omen.ingest.synthesizer.prompts.loader import load_tier_prompts
from omen.ingest.synthesizer.prompts.registry import (
    ensure_analyze_prompt_available,
    get_analyze_prompt_version_token,
    resolve_analyze_prompt_binding,
)


def test_load_base_prompt_templates() -> None:
    prompts = load_tier_prompts("base")

    assert "persona_insight" in prompts
    assert "{actor_name}" in prompts["persona_insight"]


def test_situation_decompose_prompt_requires_full_resistance_schema() -> None:
    prompts = load_tier_prompts("base")
    prompt = prompts["situation_decompose_prompt"]

    assert "structural_conflict" in prompt
    assert "resource_reallocation_drag" in prompt
    assert "cultural_misalignment" in prompt
    assert "veto_node_intensity" in prompt
    assert "aggregate_resistance" in prompt
    assert "assumption_rationale" in prompt


def test_analyze_prompt_bindings_match_open_pro_split() -> None:
    assert resolve_analyze_prompt_binding("persona").tier == "base"


def test_ensure_analyze_prompt_available_returns_binding() -> None:
    binding = ensure_analyze_prompt_available("persona")

    assert binding.command == "persona"
    assert binding.template_key == "persona_insight"


def test_analyze_prompt_version_tokens_come_from_yaml_meta() -> None:
    assert get_analyze_prompt_version_token("persona") == "base.persona_insight@1.0.0"
