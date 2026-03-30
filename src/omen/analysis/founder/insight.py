"""LLM Insight engine for deep Persona & Strategy Gap analysis."""

from __future__ import annotations

import datetime
import json
from typing import Any

from omen.ingest.llm_ontology.clients import create_chat_client
from omen.ingest.llm_ontology.config import load_llm_config
from omen.ingest.llm_ontology.dimension_loaders import load_actor_dimensions
from omen.ingest.llm_ontology.prompt_registry import get_analyze_prompt_version_token
from omen.ingest.llm_ontology.prompts import (
    build_founder_gap_prompt,
    build_founder_why_prompt,
    build_json_retry_prompt,
    build_persona_insight_prompt,
)


def _normalize_output_language(value: str | None) -> str:
    lang = str(value or "").strip().lower()
    if lang.startswith("zh"):
        return "zh"
    return "en"


def _language_instruction(output_language: str) -> str:
    if output_language == "zh":
        return "Output language requirement: All natural-language fields must be written in Simplified Chinese (简体中文)."
    return "Output language requirement: All natural-language fields must be written in English."


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM response does not contain a JSON object")
    payload, _ = decoder.raw_decode(text[start:])
    if not isinstance(payload, dict):
        raise ValueError("LLM response JSON payload is not an object")
    return payload


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    start = text.find("[")
    if start == -1:
        raise ValueError("LLM response does not contain a JSON array")
    payload, _ = decoder.raw_decode(text[start:])
    if not isinstance(payload, list):
        raise ValueError("LLM response JSON payload is not an array")
    return [item for item in payload if isinstance(item, dict)]


def _invoke_json_prompt(llm_client: Any, prompt: str, *, expect: str) -> Any:
    response = llm_client.invoke(prompt)
    content = response.content if isinstance(response.content, str) else json.dumps(response.content)
    try:
        if expect == "object":
            return _extract_json_object(content)
        return _extract_json_array(content)
    except Exception:
        retry_prompt = build_json_retry_prompt(prompt)
        retry_response = llm_client.invoke(retry_prompt)
        retry_content = (
            retry_response.content
            if isinstance(retry_response.content, str)
            else json.dumps(retry_response.content)
        )
        if expect == "object":
            return _extract_json_object(retry_content)
        return _extract_json_array(retry_content)


def _localize_known_outcome_with_llm(
    llm_client: Any,
    *,
    known_outcome: str,
    output_language: str,
) -> str:
    text = str(known_outcome or "").strip()
    if not text:
        return ""
    prompt = (
        "You are a precise translator for product analytics text.\n"
        + _language_instruction(output_language)
        + "\nReturn JSON object only with key: localized_text."
        + " Keep meaning accurate and concise; do not add extra facts.\n\n"
        + f"Source text: {json.dumps(text, ensure_ascii=False)}"
    )
    try:
        payload = _invoke_json_prompt(llm_client, prompt, expect="object")
        localized = str(payload.get("localized_text") or "").strip()
        return localized or text
    except Exception:
        return text


def _build_insight_evidence_package(
    *,
    case_id: str,
    founder_name: str,
    founder_ontology: dict[str, Any],
    strategy_ontology: dict[str, Any] | None,
    formation_payload: dict[str, Any] | None,
    known_outcome: str,
) -> dict[str, Any]:
    founder_actor = _pick_founder_actor(founder_ontology)
    profile = founder_actor.get("profile") if isinstance(founder_actor, dict) else {}
    return {
        "case_id": case_id,
        "founder_name": founder_name,
        "known_outcome": known_outcome,
        "founder_profile": profile if isinstance(profile, dict) else {},
        "events": founder_ontology.get("events") or [],
        "influences": founder_ontology.get("influences") or [],
        "strategy_meta": (strategy_ontology or {}).get("meta") if isinstance(strategy_ontology, dict) else {},
        "strategy_constraints": ((strategy_ontology or {}).get("abox") or {}).get("constraints")
        if isinstance(strategy_ontology, dict)
        else [],
        "formation": formation_payload or {},
    }


def _enhance_persona_with_llm(
    llm_client: Any,
    *,
    founder_name: str,
    profile: dict[str, Any],
    fallback_narrative: str,
    fallback_traits: list[dict[str, Any]],
    output_language: str,
) -> tuple[str, list[dict[str, Any]], float]:
    prompt = (
        build_persona_insight_prompt()
        + "\n"
        + _language_instruction(output_language)
        + "\n\nReturn JSON object only with keys: narrative, key_traits, consistency_score."
        + " key_traits must be an array of objects with trait and evidence_summary."
        + " consistency_score must be a number in [0,1].\n\n"
        + f"Founder name: {founder_name}\n"
        + f"Profile Facts JSON: {json.dumps(profile, ensure_ascii=False)}"
    )
    try:
        payload = _invoke_json_prompt(llm_client, prompt, expect="object")
        narrative = str(payload.get("narrative") or "").strip() or fallback_narrative
        key_traits_raw = payload.get("key_traits")
        key_traits = [item for item in key_traits_raw if isinstance(item, dict)] if isinstance(key_traits_raw, list) else fallback_traits
        score_raw = payload.get("consistency_score")
        try:
            score = float(score_raw)
        except Exception:
            score = 0.85
        score = max(0.0, min(1.0, score))
        return narrative, key_traits or fallback_traits, score
    except Exception:
        return fallback_narrative, fallback_traits, 0.85


def _enhance_why_chain_with_llm(
    llm_client: Any,
    *,
    evidence_package: dict[str, Any],
    fallback_items: list[dict[str, Any]],
    output_language: str,
) -> list[dict[str, Any]]:
    prompt = (
        build_founder_why_prompt()
        + "\n"
        + _language_instruction(output_language)
        + "\n\nReturn JSON array only. Each item must contain: question, answer, evidence_refs."
        + " Generate at least 3 items focused on key founder decisions and why they formed that way.\n\n"
        + f"Evidence package JSON: {json.dumps(evidence_package, ensure_ascii=False)}"
    )
    try:
        payload = _invoke_json_prompt(llm_client, prompt, expect="array")
        items = []
        for item in payload:
            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or "").strip()
            refs_raw = item.get("evidence_refs")
            refs = [str(ref) for ref in refs_raw if str(ref).strip()] if isinstance(refs_raw, list) else []
            if question and answer:
                items.append({"question": question, "answer": answer, "evidence_refs": refs})
        while len(items) < 3 and len(fallback_items) > len(items):
            items.append(fallback_items[len(items)])
        return items[: max(3, len(items))]
    except Exception:
        return fallback_items


def _enhance_gap_analysis_with_llm(
    llm_client: Any,
    *,
    evidence_package: dict[str, Any],
    fallback_process_gaps: list[dict[str, Any]],
    fallback_outcome_gaps: list[dict[str, Any]],
    fallback_learning_loop: list[dict[str, Any]],
    output_language: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    prompt = (
        build_founder_gap_prompt()
        + "\n"
        + _language_instruction(output_language)
        + "\n\nReturn JSON object only with keys: process_gaps, outcome_gaps, learning_loop."
        + " process_gaps must have at least 3 items. Each gap item must contain assumption, observation, gap_significance, event_id, phase."
        + " outcome_gaps may be empty when evidence is insufficient. learning_loop may be empty when not supported.\n\n"
        + f"Evidence package JSON: {json.dumps(evidence_package, ensure_ascii=False)}"
    )
    try:
        payload = _invoke_json_prompt(llm_client, prompt, expect="object")

        def _normalize_gap_list(value: Any) -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            if not isinstance(value, list):
                return result
            for item in value:
                if not isinstance(item, dict):
                    continue
                assumption = str(item.get("assumption") or "").strip()
                observation = str(item.get("observation") or "").strip()
                significance = str(item.get("gap_significance") or "").strip()
                if assumption and observation and significance:
                    result.append(
                        {
                            "assumption": assumption,
                            "observation": observation,
                            "gap_significance": significance,
                            "event_id": str(item.get("event_id") or "unknown_event").strip() or "unknown_event",
                            "phase": str(item.get("phase") or "unknown_phase").strip() or "unknown_phase",
                        }
                    )
            return result

        def _normalize_learning_loop(value: Any) -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            if not isinstance(value, list):
                return result
            for item in value:
                if not isinstance(item, dict):
                    continue
                signal = str(item.get("signal") or "").strip()
                adjustment = str(item.get("adjustment") or "").strip()
                evidence_ref = str(item.get("evidence_ref") or "").strip()
                if signal and adjustment and evidence_ref:
                    result.append({"signal": signal, "adjustment": adjustment, "evidence_ref": evidence_ref})
            return result

        process_gaps = _normalize_gap_list(payload.get("process_gaps"))
        outcome_gaps = _normalize_gap_list(payload.get("outcome_gaps"))
        learning_loop = _normalize_learning_loop(payload.get("learning_loop"))

        while len(process_gaps) < 3 and len(fallback_process_gaps) > len(process_gaps):
            process_gaps.append(fallback_process_gaps[len(process_gaps)])
        if not outcome_gaps:
            outcome_gaps = fallback_outcome_gaps
        if not learning_loop:
            learning_loop = fallback_learning_loop
        return process_gaps[: max(3, len(process_gaps))], outcome_gaps, learning_loop
    except Exception:
        return fallback_process_gaps, fallback_outcome_gaps, fallback_learning_loop


def _pick_founder_actor(founder_ontology: dict[str, Any]) -> dict[str, Any]:
    actors = founder_ontology.get("actors") or []
    founder_actor = next((a for a in actors if "founder" in str(a.get("type", "")).lower()), None)
    return founder_actor or (actors[0] if actors else {})


def _extract_known_outcome(
    founder_ontology: dict[str, Any], strategy_ontology: dict[str, Any] | None
) -> str:
    strategy_meta = (strategy_ontology or {}).get("meta") if isinstance(strategy_ontology, dict) else None
    if isinstance(strategy_meta, dict):
        value = str(strategy_meta.get("known_outcome") or "").strip()
        if value and value.lower() != "unknown":
            return value

    founder_meta = founder_ontology.get("meta")
    if isinstance(founder_meta, dict):
        value = str(founder_meta.get("known_outcome") or "").strip()
        if value and value.lower() != "unknown":
            return value

    return ""


def _build_why_chain(
    founder_name: str,
    core_beliefs: list[str],
    decision_style: str,
    non_negotiables: list[str],
    constraints: list[str],
    events: list[dict[str, Any]],
    output_language: str,
) -> list[dict[str, Any]]:
    first_event = events[0] if events else {}
    second_event = events[1] if len(events) > 1 else first_event
    third_event = events[2] if len(events) > 2 else second_event

    def _event_ref(event: dict[str, Any]) -> str:
        return str(event.get("id") or event.get("event_id") or event.get("name") or "unknown_event")

    if output_language == "zh":
        why_items = [
            {
                "question": f"为什么 {founder_name} 会优先选择这条战略路径，而不是标准的流程优先方案？",
                "answer": (
                    f"因为其核心信念（如“{core_beliefs[0] if core_beliefs else '数据驱动管理'}”）"
                    f"与决策风格（“{decision_style or '原则驱动'}”）共同推动其采用证据优先的执行方式。"
                ),
                "evidence_refs": [_event_ref(first_event)],
            },
            {
                "question": "为什么这些约束没有被当作阻碍，而是被当作决策边界？",
                "answer": (
                    "创始人将约束视为边界条件，并优先守住关键非妥协项，"
                    f"如“{non_negotiables[0] if non_negotiables else '低流程负担'}”，以保持战略一致性。"
                ),
                "evidence_refs": [_event_ref(second_event)],
            },
            {
                "question": "为什么执行结果仍然会偏离最初的战略假设？",
                "answer": (
                    "外部采用压力与组织摩擦带来了现实修正，"
                    f"尤其在这些约束下：{', '.join(constraints[:2]) if constraints else '市场阻力'}。"
                ),
                "evidence_refs": [_event_ref(third_event)],
            },
        ]
    else:
        why_items = [
            {
                "question": f"Why did {founder_name} prioritize this strategic path instead of standard process-first tooling?",
                "answer": (
                    f"Because core beliefs such as '{core_beliefs[0] if core_beliefs else 'data-driven management'}' "
                    f"and decision style '{decision_style or 'principle-driven'}' pushed choices toward evidence-first execution."
                ),
                "evidence_refs": [_event_ref(first_event)],
            },
            {
                "question": f"Why were constraints not treated as blockers but as filters for decision scope?",
                "answer": (
                    "The founder framed constraints as boundary conditions and protected non-negotiables "
                    f"like '{non_negotiables[0] if non_negotiables else 'low process overhead'}' to maintain strategic coherence."
                ),
                "evidence_refs": [_event_ref(second_event)],
            },
            {
                "question": "Why did execution still diverge from the initial strategic assumption?",
                "answer": (
                    "External adoption pressure and organizational friction introduced reality adjustments, "
                    f"especially under constraints: {', '.join(constraints[:2]) if constraints else 'market resistance'}"
                ),
                "evidence_refs": [_event_ref(third_event)],
            },
        ]
    return why_items


def _build_process_gaps(
    formation_payload: dict[str, Any] | None,
    events: list[dict[str, Any]],
    output_language: str,
) -> list[dict[str, Any]]:
    process_gaps: list[dict[str, Any]] = []
    if formation_payload:
        chain = formation_payload.get("formation_chain") or {}
        exec_delta = chain.get("execution_delta") or []
        decision_logic = chain.get("decision_logic") or {}
        target_event_id = str(((formation_payload.get("query") or {}).get("target_event_id") or "unknown_event")).strip()
        phase = str(((formation_payload.get("summary") or {}).get("stage") or "unknown_phase")).strip()
        affected_targets = [
            str(item.get("target_name") or "").strip()
            for item in exec_delta
            if isinstance(item, dict)
        ]
        affected_targets = [name for name in affected_targets if name]

        if output_language == "zh":
            process_gaps.append(
                {
                    "assumption": "初始战略形成能够在线性执行中快速验证。",
                    "observation": (
                        f"执行阶段出现了 {len(exec_delta)} 个偏差点"
                        + (f"，主要影响 {', '.join(affected_targets[:2])}。" if affected_targets else "。")
                    ),
                    "gap_significance": "说明初始形成确定性与现实适配复杂度之间存在错位。",
                    "event_id": target_event_id,
                    "phase": phase,
                }
            )
            process_gaps.append(
                {
                    "assumption": "基于原则的筛选可以在不牺牲速度的前提下保持一致性。",
                    "observation": (
                        "决策逻辑保持一致，但执行仍需要额外适配迭代。"
                        if decision_logic
                        else "执行轨迹显示现实压力超出了原始决策框架。"
                    ),
                    "gap_significance": "表明战略一致性与交付摩擦可以同时存在。",
                    "event_id": target_event_id,
                    "phase": phase,
                }
            )
        else:
            process_gaps.append(
                {
                    "assumption": "Initial strategic formation would validate linearly through early execution.",
                    "observation": (
                        f"Execution produced {len(exec_delta)} delta points"
                        + (f" affecting {', '.join(affected_targets[:2])}." if affected_targets else ".")
                    ),
                    "gap_significance": "Indicates mismatch between initial formation certainty and field adaptation complexity.",
                    "event_id": target_event_id,
                    "phase": phase,
                }
            )
            process_gaps.append(
                {
                    "assumption": "Principle-based filtering would maintain consistency without speed tradeoff.",
                    "observation": (
                        "Decision logic remained coherent, but execution required additional adaptation cycles."
                        if decision_logic
                        else "Execution traces show adaptation pressure beyond original decision frame."
                    ),
                    "gap_significance": "Shows strategy coherence can coexist with delivery friction.",
                    "event_id": target_event_id,
                    "phase": phase,
                }
            )

    fallback_events = events[:3] if events else []
    while len(process_gaps) < 3:
        event = fallback_events[len(process_gaps)] if len(fallback_events) > len(process_gaps) else {}
        if output_language == "zh":
            process_gaps.append(
                {
                    "assumption": "价值主张清晰后，客户采用会自然跟随产品逻辑。",
                    "observation": "事件序列显示，采用过程仍需分阶段验证与信任建立。",
                    "gap_significance": "揭示了战略逻辑到客户行为转化的非线性特征。",
                    "event_id": str(event.get("id") or event.get("event_id") or "unknown_event"),
                    "phase": str(event.get("phase") or "unknown_phase"),
                }
            )
        else:
            process_gaps.append(
                {
                    "assumption": "Customer adoption would follow product logic once value proposition is clear.",
                    "observation": "Observed event sequence suggests adoption required staged validation and trust-building.",
                    "gap_significance": "Highlights non-linear translation from strategic logic to customer behavior.",
                    "event_id": str(event.get("id") or event.get("event_id") or "unknown_event"),
                    "phase": str(event.get("phase") or "unknown_phase"),
                }
            )

    return process_gaps[:3]


def _build_outcome_gaps(known_outcome: str, process_gaps: list[dict[str, Any]], output_language: str) -> list[dict[str, Any]]:
    if not known_outcome:
        return []

    if output_language == "zh":
        template = [
            "预期战略位置与实际市场采用速度并未完全一致。",
            "计划中的扩张节奏与目标客群真实准备度存在偏差。",
            "战略意图保持稳定，但结果呈现为渐进式收敛。",
        ]
        assumption_text = "过程层面的战略成功会直接转化为结果层面的市场成功。"
        significance_text = "用于区分执行成功与结果兑现的速度和幅度。"
        observation_prefix = "已知结果显示："
    else:
        template = [
            "Expected strategic position and actual market adoption speed were not perfectly aligned.",
            "Planned scaling rhythm diverged from observed customer readiness in target segments.",
            "Strategic intent remained stable, while realized outcomes reflected incremental convergence.",
        ]
        assumption_text = "Process-level strategic wins would transfer directly to outcome-level market results."
        significance_text = "Separates execution success from outcome realization speed and magnitude."
        observation_prefix = "Known outcome indicates:"

    result: list[dict[str, Any]] = []
    for index, statement in enumerate(template):
        base_gap = process_gaps[index] if len(process_gaps) > index else {}
        result.append(
            {
                "assumption": assumption_text,
                "observation": f"{observation_prefix} {known_outcome}。 {statement}" if output_language == "zh" else f"{observation_prefix} {known_outcome}. {statement}",
                "gap_significance": significance_text,
                "event_id": str(base_gap.get("event_id") or "unknown_event"),
                "phase": str(base_gap.get("phase") or "unknown_phase"),
            }
        )
    return result


def _extract_learning_loop(events: list[dict[str, Any]], output_language: str) -> list[dict[str, Any]]:
    loops: list[dict[str, Any]] = []
    for event in events:
        text = (
            f"{event.get('name', '')} {event.get('event', '')} {event.get('description', '')}"
        ).lower()
        if any(keyword in text for keyword in ("pivot", "adjust", "iteration", "commercial", "pilot")):
            adjustment_text = (
                "创始人通过分阶段验证与商业包装调整来修正策略。"
                if output_language == "zh"
                else "Founder adjusted strategy through phased validation and packaging choices."
            )
            loops.append(
                {
                    "signal": str(event.get("name") or event.get("event") or "event_signal"),
                    "adjustment": adjustment_text,
                    "evidence_ref": str(event.get("id") or event.get("event_id") or "unknown_event"),
                }
            )
    return loops[:2]

def generate_unified_insight(
    *,
    case_id: str,
    founder_ontology: dict[str, Any],
    strategy_ontology: dict[str, Any] | None = None,
    formation_payload: dict[str, Any] | None = None,
    llm_client: Any = None,
    config_path: str | None = None,
    output_language: str = "en",
    include_persona: bool = True,
    include_why: bool = True,
    include_gap: bool = True,
    query_type: str = "insight",
    query_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a unified insight JSON containing:
    1. Persona Narrative
    2. Strategy Gap Analysis (if formation_payload is provided)
    """
    founder_actor = _pick_founder_actor(founder_ontology)

    founder_name = founder_actor.get("name", "Unknown Founder")
    profile = founder_actor.get("profile", {})

    profile_dict = profile if isinstance(profile, dict) else {}
    loaded_dimensions = load_actor_dimensions(profile_dict)
    mental_patterns = loaded_dimensions.get("mental_patterns") or {}
    strategic_style = loaded_dimensions.get("strategic_style") or {}
    core_beliefs = [str(item) for item in (mental_patterns.get("core_beliefs") or []) if str(item).strip()]
    decision_style = str(strategic_style.get("decision_style") or "intentional")
    non_negotiables = [str(item) for item in (strategic_style.get("non_negotiables") or []) if str(item).strip()]

    constraints = [
        str(item.get("name") or item.get("id") or "").strip()
        for item in (founder_ontology.get("constraints") or [])
        if isinstance(item, dict)
    ]
    constraints = [item for item in constraints if item]
    events = [item for item in (founder_ontology.get("events") or []) if isinstance(item, dict)]

    language = _normalize_output_language(output_language)

    if language == "zh":
        fallback_persona_narrative = (
            f"{founder_name} 的决策风格与其核心信念保持高度一致："
            f"“{', '.join(core_beliefs[:2])}”。"
            f"其战略风格体现为“{decision_style}”，"
            f"在外部压力下仍优先守住“{', '.join(non_negotiables[:1])}”等非妥协项。"
            "这体现出其创始人画像具备明显的原则驱动特征，更强调证据与内在逻辑而非传统流程惯性。"
        )
        fallback_key_traits = [
            {"trait": "原则驱动", "evidence_summary": "在关键战略决策中优先守住非妥协项。"},
            {"trait": "证据导向", "evidence_summary": "通过数据与信号构建市场认知与判断。"},
        ]
    else:
        fallback_persona_narrative = (
            f"{founder_name} is characterized by a strong alignment with their core beliefs: "
            f"'{', '.join(core_beliefs[:2])}'. "
            f"Their strategic style reflects a '{decision_style}' approach, "
            f"often prioritizing '{', '.join(non_negotiables[:1])}' over external pressures. "
            "This indicates a founder persona that is deeply principle-driven, favoring evidence and internal logic over conventional process."
        )
        fallback_key_traits = [
            {"trait": "Principle-Driven", "evidence_summary": "Prioritizes non-negotiables in strategic decisions."},
            {"trait": "Evidence-Based", "evidence_summary": "Uses data/signals for market perception."},
        ]
    
    fallback_why_chain = _build_why_chain(
        founder_name=founder_name,
        core_beliefs=core_beliefs,
        decision_style=decision_style,
        non_negotiables=non_negotiables,
        constraints=constraints,
        events=events,
        output_language=language,
    )

    fallback_process_gaps = _build_process_gaps(
        formation_payload=formation_payload,
        events=events,
        output_language=language,
    )
    known_outcome = _extract_known_outcome(founder_ontology, strategy_ontology)
    fallback_learning_loop = _extract_learning_loop(events, output_language=language)

    effective_llm_client = llm_client
    if effective_llm_client is None and config_path:
        try:
            llm_config = load_llm_config(config_path, require_embeddings=False)
            effective_llm_client = create_chat_client(llm_config)
        except Exception:
            effective_llm_client = None

    output_known_outcome = known_outcome
    if effective_llm_client is not None and known_outcome and language == "zh":
        output_known_outcome = _localize_known_outcome_with_llm(
            effective_llm_client,
            known_outcome=known_outcome,
            output_language=language,
        )

    fallback_outcome_gaps = _build_outcome_gaps(
        known_outcome=output_known_outcome,
        process_gaps=fallback_process_gaps,
        output_language=language,
    )

    evidence_package = _build_insight_evidence_package(
        case_id=case_id,
        founder_name=founder_name,
        founder_ontology=founder_ontology,
        strategy_ontology=strategy_ontology,
        formation_payload=formation_payload,
        known_outcome=output_known_outcome,
    )

    persona_narrative = fallback_persona_narrative
    key_traits = fallback_key_traits
    consistency_score = 0.85
    why_chain = fallback_why_chain
    process_gaps = fallback_process_gaps
    outcome_gaps = fallback_outcome_gaps
    learning_loop = fallback_learning_loop

    if effective_llm_client is not None:
        if include_persona:
            persona_narrative, key_traits, consistency_score = _enhance_persona_with_llm(
                effective_llm_client,
                founder_name=founder_name,
                profile=profile_dict,
                fallback_narrative=fallback_persona_narrative,
                fallback_traits=fallback_key_traits,
                output_language=language,
            )
        if include_why:
            why_chain = _enhance_why_chain_with_llm(
                effective_llm_client,
                evidence_package=evidence_package,
                fallback_items=fallback_why_chain,
                output_language=language,
            )
        if include_gap:
            process_gaps, outcome_gaps, learning_loop = _enhance_gap_analysis_with_llm(
                effective_llm_client,
                evidence_package=evidence_package,
                fallback_process_gaps=fallback_process_gaps,
                fallback_outcome_gaps=fallback_outcome_gaps,
                fallback_learning_loop=fallback_learning_loop,
                output_language=language,
            )

    query_payload: dict[str, Any] = {
        "type": query_type,
        "case_id": case_id,
    }
    if query_context:
        query_payload.update(query_context)
    if formation_payload:
        target_event_id = (formation_payload.get("query") or {}).get("target_event_id")
        if isinstance(target_event_id, str) and target_event_id.strip():
            query_payload["target_event_id"] = target_event_id.strip()

    prompt_tokens: list[str] = []
    if include_persona:
        prompt_tokens.append(get_analyze_prompt_version_token("persona"))
    if include_why:
        prompt_tokens.append(get_analyze_prompt_version_token("why"))
    if include_gap:
        prompt_tokens.append(get_analyze_prompt_version_token("insight"))
    prompt_version = ",".join(prompt_tokens) if prompt_tokens else "unknown@unknown"

    insight_result = {
        "query": query_payload,
        "run_meta": {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt_version": prompt_version,
            "mode": "llm-enhanced" if effective_llm_client is not None else "skeleton-deterministic",
        }
    }

    if include_persona:
        insight_result["persona_insight"] = {
            "narrative": persona_narrative,
            "key_traits": key_traits,
            "consistency_score": consistency_score,
        }

    if include_why:
        insight_result["why_chain"] = why_chain

    if include_gap:
        insight_result["gap_analysis"] = {
            "process_gaps": process_gaps,
            "outcome_gaps": outcome_gaps,
            "learning_loop": learning_loop,
            "known_outcome": output_known_outcome,
        }
    
    return insight_result


def generate_persona_insight(
    *,
    case_id: str,
    founder_ontology: dict[str, Any],
    strategy_ontology: dict[str, Any] | None = None,
    llm_client: Any = None,
    config_path: str | None = None,
    output_language: str = "en",
) -> dict[str, Any]:
    return generate_unified_insight(
        case_id=case_id,
        founder_ontology=founder_ontology,
        strategy_ontology=strategy_ontology,
        llm_client=llm_client,
        config_path=config_path,
        output_language=output_language,
        include_persona=True,
        include_why=False,
        include_gap=False,
        query_type="persona",
    )


def generate_why_insight(
    *,
    case_id: str,
    founder_ontology: dict[str, Any],
    strategy_ontology: dict[str, Any] | None = None,
    formation_payload: dict[str, Any] | None = None,
    decision_id: str | None = None,
    llm_client: Any = None,
    config_path: str | None = None,
    output_language: str = "en",
) -> dict[str, Any]:
    query_context = {"decision_id": decision_id} if decision_id else None
    return generate_unified_insight(
        case_id=case_id,
        founder_ontology=founder_ontology,
        strategy_ontology=strategy_ontology,
        formation_payload=formation_payload,
        llm_client=llm_client,
        config_path=config_path,
        output_language=output_language,
        include_persona=False,
        include_why=True,
        include_gap=False,
        query_type="why",
        query_context=query_context,
    )
