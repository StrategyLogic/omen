"""Actor OSS insight capability surface.
"""

from __future__ import annotations

import datetime
from typing import Any

from omen.ingest.llm_ontology.prompt_registry import get_analyze_prompt_version_token


def _normalize_output_language(value: str | None) -> str:
    lang = str(value or "").strip().lower()
    if lang.startswith("zh"):
        return "zh"
    return "en"


def _pick_primary_actor(actor_ontology: dict[str, Any]) -> dict[str, Any]:
    actors = actor_ontology.get("actors") or []
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        actor_type = str(actor.get("type") or "").strip().lower()
        if actor_type == "strategicactor":
            return actor
    for actor in actors:
        if isinstance(actor, dict):
            return actor
    return {}


def generate_persona_insight(
    *,
    case_id: str,
    actor_ontology: dict[str, Any],
    strategy_ontology: dict[str, Any] | None = None,
    llm_client: Any = None,
    config_path: str | None = None,
    output_language: str = "en",
) -> dict[str, Any]:
    del strategy_ontology, llm_client, config_path

    actor = _pick_primary_actor(actor_ontology)
    actor_name = str(actor.get("name") or "Strategic Actor").strip() or "Strategic Actor"
    profile = actor.get("profile") or {}
    profile_dict = profile if isinstance(profile, dict) else {}

    mental_patterns = profile_dict.get("mental_patterns") or {}
    strategic_style = profile_dict.get("strategic_style") or {}
    core_beliefs = [str(item).strip() for item in (mental_patterns.get("core_beliefs") or []) if str(item).strip()]
    non_negotiables = [str(item).strip() for item in (strategic_style.get("non_negotiables") or []) if str(item).strip()]
    decision_style = str(strategic_style.get("decision_style") or "intentional").strip() or "intentional"

    language = _normalize_output_language(output_language)
    if language == "zh":
        narrative = (
            f"{actor_name} 的战略行为呈现明显的原则驱动特征，"
            f"决策风格为“{decision_style}”，"
            f"核心信念聚焦在“{core_beliefs[0] if core_beliefs else '长期价值'}”，"
            f"并持续守住“{non_negotiables[0] if non_negotiables else '关键非妥协项'}”。"
        )
        key_traits = [
            {"trait": "原则驱动", "evidence_summary": "在约束条件下保持战略一致性。"},
            {"trait": "结构化判断", "evidence_summary": "以证据和逻辑链条组织决策。"},
        ]
    else:
        narrative = (
            f"{actor_name} shows a principle-driven strategic profile with a '{decision_style}' decision style, "
            f"anchored in '{core_beliefs[0] if core_beliefs else 'long-term value'}' and guarded by "
            f"'{non_negotiables[0] if non_negotiables else 'clear non-negotiables'}'."
        )
        key_traits = [
            {"trait": "Principle-Driven", "evidence_summary": "Maintains coherence under constraints."},
            {"trait": "Structured Reasoning", "evidence_summary": "Uses evidence-based decision framing."},
        ]

    return {
        "query": {"type": "persona", "case_id": case_id},
        "run_meta": {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt_version": get_analyze_prompt_version_token("persona"),
            "mode": "skeleton-deterministic",
        },
        "persona_insight": {
            "narrative": narrative,
            "key_traits": key_traits,
            "consistency_score": 0.85,
        },
    }
