"""LLM services for situation extraction/enhancement and scenario decomposition."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from omen.ingest.synthesizer.clients import invoke_text_prompt, render_prompt_template
from omen.ingest.synthesizer.prompts import build_json_retry_prompt
from omen.ingest.synthesizer.prompts.registry import get_prompt_template


_RISK_CONFIDENCE_MIN = 0.2
_RISK_DECAY_LAMBDA = 0.15
_CONFIDENCE_DELTA_MAX = 0.5


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM response does not contain JSON object")
    payload, _ = decoder.raw_decode(text[start:])
    if not isinstance(payload, dict):
        raise ValueError("LLM response payload is not an object")
    return payload


def _invoke_json(prompt: str, *, config_path: str) -> dict[str, Any]:
    content = invoke_text_prompt(config_path=config_path, user_prompt=prompt)
    try:
        return _extract_json_object(content)
    except Exception:
        retry_prompt = build_json_retry_prompt(prompt)
        retry_content = invoke_text_prompt(config_path=config_path, user_prompt=retry_prompt)
        return _extract_json_object(retry_content)


def _read_source_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _render_base_prompt(template_key: str, values: dict[str, object]) -> str:
    return render_prompt_template(get_prompt_template(template_key, tier="base"), values)


def _as_dict_list(value: Any, *, key_name: str = "name") -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            normalized.append(item)
            continue
        text = str(item).strip()
        if text:
            normalized.append({key_name: text})
    return normalized


def _normalize_uncertainty_space(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        output = dict(value)
        output.setdefault("overall_confidence", 0.5)
        output.setdefault("high_leverage_unknowns", [])
        output.setdefault("assumptions_explicit", [])
        return output

    if isinstance(value, list):
        unknowns = [str(item).strip() for item in value if str(item).strip()]
        return {
            "overall_confidence": 0.5,
            "high_leverage_unknowns": unknowns,
            "assumptions_explicit": [],
        }

    return {
        "overall_confidence": 0.5,
        "high_leverage_unknowns": [],
        "assumptions_explicit": [],
    }


def _normalize_source_trace(value: Any, *, source_path: str, situation_id: str) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]

    if isinstance(value, dict):
        return [value]

    return [
        {
            "situation_id": situation_id,
            "source_path": source_path,
        }
    ]


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


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_assumptions_explicit(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    output: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            target_unknown = str(item.get("target_unknown") or "").strip()
            assumption_text = str(item.get("assumption_text") or item.get("text") or "").strip()
            quality_score = _to_float(item.get("quality_score"))
            if quality_score is None:
                quality_score = 0.7 if assumption_text else 0.0
            output.append(
                {
                    "target_unknown": target_unknown,
                    "assumption_text": assumption_text,
                    "quality_score": _clamp_01(quality_score),
                    "coverage_type": str(item.get("coverage_type") or "direct").strip() or "direct",
                }
            )
            continue

        text = str(item).strip()
        if text:
            output.append(
                {
                    "target_unknown": "",
                    "assumption_text": text,
                    "quality_score": 0.7,
                    "coverage_type": "direct",
                }
            )
    return output


def _compute_dual_confidence(
    *,
    context: dict[str, Any],
    uncertainty_space: dict[str, Any],
) -> dict[str, Any]:
    known_unknowns = [str(item).strip() for item in (context.get("known_unknowns") or []) if str(item).strip()]
    unknown_count = len(known_unknowns)

    confidence_risk = max(_RISK_CONFIDENCE_MIN, 1.0 - (_RISK_DECAY_LAMBDA * unknown_count))

    assumptions = _normalize_assumptions_explicit(uncertainty_space.get("assumptions_explicit"))
    assumption_count = len(assumptions)
    quality_sum = sum(float(item.get("quality_score") or 0.0) for item in assumptions)
    quality_avg = (quality_sum / assumption_count) if assumption_count else 0.0

    if unknown_count == 0:
        coverage_ratio = 1.0
    elif assumption_count == 0:
        coverage_ratio = 0.0
    else:
        coverage_ratio = min(1.0, quality_sum / float(unknown_count))

    computed_overall = confidence_risk + (1.0 - confidence_risk) * coverage_ratio
    llm_overall = _to_float(uncertainty_space.get("overall_confidence"))
    if llm_overall is None:
        confidence_overall = _clamp_01(computed_overall)
    else:
        confidence_overall = _clamp_01(llm_overall)

    guardrail_applied = False
    if confidence_overall - confidence_risk > _CONFIDENCE_DELTA_MAX:
        confidence_overall = confidence_risk + _CONFIDENCE_DELTA_MAX
        guardrail_applied = True

    return {
        "confidence_risk": round(_clamp_01(confidence_risk), 4),
        "confidence_overall": round(_clamp_01(confidence_overall), 4),
        "coverage_ratio": round(_clamp_01(coverage_ratio), 4),
        "guardrail_applied": guardrail_applied,
        "assumptions_explicit": assumptions,
        "metrics": {
            "known_unknowns_count": unknown_count,
            "assumptions_filled_count": assumption_count,
            "assumptions_quality_avg": round(_clamp_01(quality_avg), 4),
            "cognitive_coverage": round(_clamp_01(coverage_ratio), 4),
            "confidence_delta_cap": _CONFIDENCE_DELTA_MAX,
        },
    }


def _apply_dual_confidence_enhancement(enhanced: dict[str, Any], context: dict[str, Any]) -> None:
    uncertainty = _normalize_uncertainty_space(enhanced.get("uncertainty_space"))
    confidence = _compute_dual_confidence(context=context, uncertainty_space=uncertainty)

    uncertainty["assumptions_explicit"] = confidence["assumptions_explicit"]
    uncertainty["overall_confidence"] = confidence["confidence_overall"]
    uncertainty["confidence_risk"] = confidence["confidence_risk"]
    uncertainty["confidence_overall"] = confidence["confidence_overall"]
    uncertainty["metrics"] = confidence["metrics"]
    uncertainty["guardrail_applied"] = confidence["guardrail_applied"]

    high_leverage_unknowns = _as_dict_list(uncertainty.get("high_leverage_unknowns"), key_name="name")
    uncertainty["high_leverage_unknowns"] = [item.get("name") for item in high_leverage_unknowns if item.get("name")]
    if not uncertainty["high_leverage_unknowns"]:
        uncertainty["high_leverage_unknowns"] = [
            str(item).strip()
            for item in (context.get("known_unknowns") or [])
            if str(item).strip()
        ][:3]

    assumptions_explicit = uncertainty.get("assumptions_explicit")
    if not isinstance(assumptions_explicit, list):
        uncertainty["assumptions_explicit"] = []

    enhanced["uncertainty_space"] = uncertainty


def build_situation_confidence_trace(
    *,
    situation_artifact: dict[str, Any],
    situation_artifact_path: str | Path,
) -> dict[str, Any]:
    source_meta = situation_artifact.get("source_meta") or {}
    uncertainty = situation_artifact.get("uncertainty_space") or {}
    metrics = uncertainty.get("metrics") or {}

    return {
        "artifact_type": "situation_generation_trace",
        "situation_id": str(situation_artifact.get("id") or "unknown"),
        "situation_artifact_path": str(situation_artifact_path),
        "source_path": str(source_meta.get("source_path") or ""),
        "pack_id": str(source_meta.get("pack_id") or ""),
        "pack_version": str(source_meta.get("pack_version") or ""),
        "generated_at": str(source_meta.get("generated_at") or datetime.now().isoformat()),
        "validation_passed": True,
        "validation_issues": [],
        "confidence": {
            "confidence_risk": uncertainty.get("confidence_risk"),
            "confidence_overall": uncertainty.get("confidence_overall"),
            "overall_confidence": uncertainty.get("overall_confidence"),
            "coverage_ratio": metrics.get("cognitive_coverage"),
            "guardrail_applied": bool(uncertainty.get("guardrail_applied", False)),
        },
        "metrics": metrics,
        "assumptions_explicit": uncertainty.get("assumptions_explicit") or [],
    }


def generate_situation_case_document(
    *,
    source_text: str,
    source_ref: str,
    source_text_path: str,
    config_path: str = "config/llm.toml",
) -> tuple[str, str]:
    template_path = Path("config/templates/situation_case.md")
    template_text = template_path.read_text(encoding="utf-8")

    payload = _invoke_json(
        _render_base_prompt(
            "situation_source_to_case_prompt",
            {
                "source_ref": source_ref,
                "source_text_path": source_text_path,
                "source_text": source_text,
            },
        ),
        config_path=config_path,
    )

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
            "capture_date": datetime.now().date().isoformat(),
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


def analyze_situation_document(
    *,
    situation_file: str | Path,
    actor_ref: str | None,
    pack_id: str,
    pack_version: str,
    config_path: str = "config/llm.toml",
) -> dict[str, Any]:
    path = Path(situation_file)
    source_text = _read_source_text(path)
    situation_id = path.stem

    context = _invoke_json(
        _render_base_prompt(
            "situation_extract_prompt",
            {
                "actor_ref": actor_ref or "none",
                "source_path": str(path),
                "source_text": source_text,
            },
        ),
        config_path=config_path,
    )

    enhanced = _invoke_json(
        _render_base_prompt(
            "situation_enhance_prompt",
            {
                "situation_id": situation_id,
                "source_path": str(path),
                "context_json": json.dumps(context, ensure_ascii=False),
                "source_text": source_text,
            },
        ),
        config_path=config_path,
    )

    enhanced.setdefault("version", "0.1.0")
    enhanced.setdefault("id", situation_id)
    enhanced.setdefault("context", context)
    enhanced["signals"] = _as_dict_list(enhanced.get("signals"), key_name="name")
    if not enhanced["signals"]:
        enhanced["signals"] = [{"name": "Signal extracted from source document"}]
    enhanced["tech_space_seed"] = _as_dict_list(enhanced.get("tech_space_seed"), key_name="name")
    enhanced["market_space_seed"] = _as_dict_list(enhanced.get("market_space_seed"), key_name="name")
    _apply_dual_confidence_enhancement(enhanced, context)
    enhanced["source_trace"] = _normalize_source_trace(
        enhanced.get("source_trace"),
        source_path=str(path),
        situation_id=situation_id,
    )
    enhanced["source_meta"] = {
        "source_path": str(path),
        "generated_at": datetime.now().isoformat(),
        "pack_id": pack_id,
        "pack_version": pack_version,
        "actor_ref": actor_ref,
    }
    return enhanced


def decompose_scenario_from_situation(
    *,
    situation_artifact: dict[str, Any],
    pack_id: str,
    pack_version: str,
    config_path: str = "config/llm.toml",
    planning_template: dict[str, Any] | None = None,
    planning_query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _invoke_json(
        _render_base_prompt(
            "situation_decompose_prompt",
            {
                "pack_id": pack_id,
                "pack_version": pack_version,
                "situation_artifact_json": json.dumps(situation_artifact, ensure_ascii=False),
                "planning_template_json": json.dumps(planning_template or {}, ensure_ascii=False),
                "planning_query_json": json.dumps(planning_query or {}, ensure_ascii=False),
            },
        ),
        config_path=config_path,
    )

    payload.setdefault("pack_id", pack_id)
    payload.setdefault("pack_version", pack_version)
    payload.setdefault("derived_from_situation_id", str(situation_artifact.get("id") or "unknown"))
    payload.setdefault("ontology_version", "scenario_ontology_v1")
    payload.setdefault("scenarios", [])
    payload.setdefault(
        "source_meta",
        {
            "source_path": str((situation_artifact.get("source_meta") or {}).get("source_path") or ""),
            "generated_at": datetime.now().isoformat(),
            "generated_from": "situation_artifact",
        },
    )
    return payload
