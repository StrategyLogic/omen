"""Situation builders for source parsing, enhancement, and confidence artifacts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from omen.ingest.synthesizer.clients import invoke_json_prompt, render_prompt_template
from omen.ingest.synthesizer.prompts import build_json_retry_prompt
from omen.ingest.synthesizer.prompts.registry import get_prompt_template
from omen.ingest.synthesizer.services.errors import LLMJsonValidationAbort


_RISK_CONFIDENCE_MIN = 0.2
_RISK_DECAY_LAMBDA = 0.15
_CONFIDENCE_DELTA_MAX = 0.5
_SIGNAL_IMPACT_TYPES = {"driver", "constraint", "amplifier", "dampener"}
_SIGNAL_DIRECTION_VALUES = {"up", "down", "mixed"}
_SIGNAL_DOMAIN_VALUES = {"tech", "market", "capital", "standard", "policy"}
_SIGNAL_EXPECTED_LAG_VALUES = {"short", "medium", "long"}

def _invoke_json(
    prompt: str,
    *,
    allow_retry: bool = True,
    stage: str = "llm_json",
) -> dict[str, Any]:
    retry_prompt = build_json_retry_prompt(prompt) if allow_retry else None
    payload = invoke_json_prompt(
        user_prompt=prompt,
        allow_retry=allow_retry,
        retry_prompt=retry_prompt,
        stage=stage,
        expected_type="object",
    )
    if not isinstance(payload, dict):
        raise LLMJsonValidationAbort(
            stage=stage,
            reason="parsed payload is not an object",
            raw_output=json.dumps(payload, ensure_ascii=False),
        )
    return payload


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


def _load_yaml_template(path: str | Path) -> dict[str, Any]:
    template_path = Path(path)
    if not template_path.is_absolute() and not template_path.exists():
        repo_root = Path(__file__).resolve().parents[5]
        template_path = repo_root / template_path

    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"template must be a YAML object: {template_path}")
    return payload


def _slugify_token(value: str, *, prefix: str) -> str:
    base = _slugify_case_name(value)
    return f"{prefix}-{base}" if base else f"{prefix}-item"


def _normalize_signal_impact_type(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text == "dampencer":
        text = "dampener"
    if text in _SIGNAL_IMPACT_TYPES:
        return text
    return "driver"


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_signal_strength(value: Any) -> float:
    if isinstance(value, (int, float)):
        return _clamp_01(float(value))

    text = str(value or "").strip().lower()
    if text in {"low", "weak"}:
        return 0.3
    if text in {"high", "strong"}:
        return 0.8
    if text in {"medium", "mid", "moderate"}:
        return 0.5

    parsed = _to_float(value)
    if parsed is None:
        return 0.5
    return _clamp_01(parsed)


def _normalize_signal_direction(value: Any, *, impact_type: str, direction_defaults: dict[str, Any]) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    alias = {
        "positive": "up",
        "negative": "down",
        "uncertain": "mixed",
    }
    text = alias.get(text, text)
    if text in _SIGNAL_DIRECTION_VALUES:
        return text

    fallback = str(direction_defaults.get(impact_type) or "").strip().lower()
    fallback = alias.get(fallback, fallback)
    if fallback in _SIGNAL_DIRECTION_VALUES:
        return fallback
    return "mixed"


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item).strip())]


def _default_signal_effect(*, direction: str, impact_type: str, target_ref: str) -> str:
    if direction == "up":
        return f"Strengthens momentum around {target_ref} as a {impact_type}."
    if direction == "down":
        return f"Increases pressure or drag on {target_ref} as a {impact_type}."
    if direction == "mixed":
        return f"Reshapes {target_ref} through offsetting strategic effects."
    return f"Reshapes {target_ref} through offsetting strategic effects."


def _normalize_target_mechanism_conditions(
    value: dict[str, Any],
    *,
    impact_type: str,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    conditions: dict[str, Any] = {}

    expected_effect = str(value.get("expected_effect") or fallback.get("expected_effect") or "").strip()
    conditions["expected_effect"] = expected_effect or "Moves the mapped target trajectory in the declared direction."

    if impact_type == "driver":
        activation = str(value.get("activation_condition") or fallback.get("activation_condition") or "").strip()
        conditions["activation_condition"] = activation or "Active under current strategic pressure."
    elif impact_type == "constraint":
        binding = str(value.get("binding_condition") or fallback.get("binding_condition") or "").strip()
        release = str(value.get("release_condition") or fallback.get("release_condition") or "").strip()
        conditions["binding_condition"] = binding or "Constraint binds under external pressure."
        conditions["release_condition"] = release or "Constraint relaxes when leverage shifts."
    else:
        target = str(value.get("modulation_target") or fallback.get("modulation_target") or "primary_driver").strip()
        modulation_condition = str(value.get("modulation_condition") or fallback.get("modulation_condition") or "").strip()
        modulation_factor = _normalize_signal_strength(value.get("modulation_factor"))
        conditions["modulation_target"] = target or "primary_driver"
        conditions["modulation_condition"] = (
            modulation_condition or "Modulation applies when adjacent signals co-move."
        )
        conditions["modulation_factor"] = modulation_factor

    return conditions


def _normalize_signal_targets(
    value: Any,
    *,
    impact_type: str,
    direction: str,
    default_target_space: str,
    default_impact_strength: float,
    signal_name: str,
    context: dict[str, Any],
    fallback: dict[str, Any],
) -> list[dict[str, Any]]:
    if isinstance(value, str):
        value = [value]

    targets: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                space = str(item.get("space") or default_target_space).strip() or default_target_space
                if space not in {"TechSpace", "MarketSpace"}:
                    space = default_target_space
                element_key = str(item.get("element_key") or item.get("target_ref") or item.get("ref") or item.get("name") or "").strip()
                if not element_key:
                    continue
                target_impact_type = _normalize_signal_impact_type(item.get("impact_type") or impact_type)
                impact_strength = _normalize_signal_strength(item.get("impact_strength") or item.get("strength"))
                mechanism = item.get("mechanism_conditions")
                mechanism_conditions = mechanism if isinstance(mechanism, dict) else {}
                expected_effect = str(
                    mechanism_conditions.get("expected_effect")
                    or item.get("effect")
                    or _default_signal_effect(
                        direction=direction,
                        impact_type=target_impact_type,
                        target_ref=element_key,
                    )
                ).strip()
                mechanism_conditions.setdefault("expected_effect", expected_effect)
                mechanism_conditions = _normalize_target_mechanism_conditions(
                    mechanism_conditions,
                    impact_type=target_impact_type,
                    fallback=fallback,
                )
                targets.append(
                    {
                        "space": space,
                        "element_key": element_key,
                        "impact_type": target_impact_type,
                        "impact_strength": impact_strength,
                        "mechanism_conditions": mechanism_conditions,
                    }
                )
                continue

            element_key = str(item).strip()
            if element_key:
                target_impact_type = impact_type
                targets.append(
                    {
                        "space": default_target_space,
                        "element_key": element_key,
                        "impact_type": target_impact_type,
                        "impact_strength": default_impact_strength,
                        "mechanism_conditions": _normalize_target_mechanism_conditions(
                            {
                                "expected_effect": _default_signal_effect(
                                    direction=direction,
                                    impact_type=target_impact_type,
                                    target_ref=element_key,
                                )
                            },
                            impact_type=target_impact_type,
                            fallback=fallback,
                        ),
                    }
                )

    if targets:
        return targets

    fallback_target = str(context.get("core_question") or context.get("title") or signal_name).strip()
    target_impact_type = impact_type
    return [
        {
            "space": default_target_space,
            "element_key": fallback_target,
            "impact_type": target_impact_type,
            "impact_strength": default_impact_strength,
            "mechanism_conditions": _normalize_target_mechanism_conditions(
                {
                    "expected_effect": _default_signal_effect(
                        direction=direction,
                        impact_type=target_impact_type,
                        target_ref=fallback_target,
                    )
                },
                impact_type=target_impact_type,
                fallback=fallback,
            ),
        }
    ]


def _normalize_signal_cascade_rules(
    value: Any,
    *,
    signal_id: str,
    fallback: dict[str, Any],
    default_expected_lag: str,
) -> tuple[list[dict[str, str]], str | None]:
    no_cascade_reason = ""
    rules: list[dict[str, str]] = []

    if isinstance(value, dict):
        value = [value]

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                trigger = str(item.get("trigger_condition") or "").strip()
                next_signal_id = str(item.get("next_signal_id") or "").strip()
                expected_lag = str(item.get("expected_lag") or default_expected_lag).strip().lower()
                if expected_lag not in _SIGNAL_EXPECTED_LAG_VALUES:
                    expected_lag = default_expected_lag
                if trigger and next_signal_id:
                    rules.append(
                        {
                            "trigger_condition": trigger,
                            "next_signal_id": next_signal_id,
                            "expected_lag": expected_lag,
                        }
                    )
                continue

            text = str(item).strip()
            if text:
                rules.append(
                    {
                        "trigger_condition": text,
                        "next_signal_id": signal_id,
                        "expected_lag": default_expected_lag,
                    }
                )

    if rules:
        return rules, None

    no_cascade_reason = str(fallback.get("no_cascade_reason") or "direct local effect in current horizon").strip()
    return [], (no_cascade_reason or "direct local effect in current horizon")


def _normalize_market_constraints(
    value: Any,
    *,
    context: dict[str, Any],
    fallback: dict[str, Any],
    default_binding_strength: float,
) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = []

    if isinstance(value, dict):
        value = [value]

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                constraint_key = str(item.get("constraint_key") or item.get("name") or "").strip()
                if not constraint_key:
                    continue
                binding_strength = _normalize_signal_strength(item.get("binding_strength"))
                constraints.append(
                    {
                        "constraint_key": constraint_key,
                        "binding_strength": binding_strength,
                    }
                )
                continue

            constraint_key = str(item).strip()
            if constraint_key:
                constraints.append(
                    {
                        "constraint_key": constraint_key,
                        "binding_strength": default_binding_strength,
                    }
                )

    if constraints:
        return constraints

    hard_constraints = _normalize_string_list(context.get("hard_constraints"))
    if hard_constraints:
        return [
            {
                "constraint_key": item,
                "binding_strength": default_binding_strength,
            }
            for item in hard_constraints[:2]
        ]

    return [
        {
            "constraint_key": str(fallback.get("market_constraint") or "market_friction"),
            "binding_strength": default_binding_strength,
        }
    ]


def _normalize_situation_signals(
    value: Any,
    *,
    situation_id: str,
    context: dict[str, Any],
    signal_template: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        value = []

    defaults = dict((signal_template.get("signal_schema") or {}).get("defaults") or {})
    fallback = dict(signal_template.get("fallbacks") or {})
    direction_defaults = dict(defaults.get("direction_by_impact_type") or {})
    default_domain = str(defaults.get("domain") or "market").strip() or "market"
    default_target_space = str(defaults.get("mapped_target_space") or "MarketSpace").strip() or "MarketSpace"
    default_impact_strength = _normalize_signal_strength(defaults.get("impact_strength"))
    default_expected_lag = str(defaults.get("expected_lag") or "medium").strip().lower()
    if default_expected_lag not in _SIGNAL_EXPECTED_LAG_VALUES:
        default_expected_lag = "medium"
    default_binding_strength = _normalize_signal_strength(defaults.get("market_binding_strength"))

    normalized: list[dict[str, Any]] = []

    for index, item in enumerate(value, start=1):
        if isinstance(item, dict):
            raw = dict(item)
            name = str(raw.get("name") or raw.get("signal") or raw.get("title") or "").strip()
        else:
            raw = {}
            name = str(item).strip()

        if not name:
            continue

        impact_type = _normalize_signal_impact_type(
            raw.get("impact_type") or raw.get("type") or raw.get("kind") or raw.get("role")
        )
        direction = _normalize_signal_direction(
            raw.get("direction"),
            impact_type=impact_type,
            direction_defaults=direction_defaults,
        )
        domain = str(raw.get("domain") or default_domain).strip().lower().replace(" ", "_") or default_domain
        if domain not in _SIGNAL_DOMAIN_VALUES:
            domain = default_domain
        strength = _normalize_signal_strength(raw.get("strength"))
        signal_id = str(raw.get("id") or _slugify_token(f"{situation_id}-{index}-{name}", prefix="sig"))
        mapped_targets = _normalize_signal_targets(
            raw.get("mapped_targets") or raw.get("targets"),
            impact_type=impact_type,
            direction=direction,
            default_target_space=default_target_space,
            default_impact_strength=default_impact_strength,
            signal_name=name,
            context=context,
            fallback=fallback,
        )

        cascade_rules, no_cascade_reason = _normalize_signal_cascade_rules(
            raw.get("cascade_rules") or raw.get("downstream_effects"),
            signal_id=signal_id,
            fallback=fallback,
            default_expected_lag=default_expected_lag,
        )

        market_constraints = _normalize_market_constraints(
            raw.get("market_constraints"),
            context=context,
            fallback=fallback,
            default_binding_strength=default_binding_strength,
        )

        mechanism_note = str(raw.get("mechanism_note") or "").strip()
        if not mechanism_note:
            mechanism_note = (
                f"{name} functions as a {impact_type} in the {domain} domain and directly shapes "
                f"{mapped_targets[0]['element_key']} under the current situation."
            )

        normalized_signal = {
            "id": signal_id,
            "name": name,
            "domain": domain,
            "strength": strength,
            "direction": direction,
            "mapped_targets": mapped_targets,
            "cascade_rules": cascade_rules,
            "market_constraints": market_constraints,
            "mechanism_note": mechanism_note,
        }
        if no_cascade_reason:
            normalized_signal["no_cascade_reason"] = no_cascade_reason

        normalized.append(normalized_signal)

    return normalized


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


def analyze_situation_document(
    *,
    situation_file: str | Path,
    actor_ref: str | None,
    pack_id: str,
    pack_version: str,
) -> dict[str, Any]:
    path = Path(situation_file)
    source_text = _read_source_text(path)
    situation_id = path.stem
    signal_template = _load_yaml_template("config/templates/signals.yaml")

    context = _invoke_json(
        _render_base_prompt(
            "situation_extract_prompt",
            {
                "actor_ref": actor_ref or "none",
                "source_path": str(path),
                "source_text": source_text,
            },
        ),
    )

    enhanced = _invoke_json(
        _render_base_prompt(
            "situation_enhance_prompt",
            {
                "situation_id": situation_id,
                "source_path": str(path),
                "context_json": json.dumps(context, ensure_ascii=False),
                "signals_template_json": json.dumps(signal_template, ensure_ascii=False),
                "source_text": source_text,
            },
        ),
        allow_retry=False,
        stage="situation_enhance_prompt",
    )

    llm_signals = enhanced.get("signals")
    if not isinstance(llm_signals, list) or not llm_signals:
        raise LLMJsonValidationAbort(
            stage="situation_enhance_prompt",
            reason="missing or empty `signals` in enhance response",
            raw_output=json.dumps(enhanced, ensure_ascii=False),
        )

    enhanced.setdefault("version", "0.1.0")
    enhanced.setdefault("id", situation_id)
    enhanced.setdefault("context", context)
    enhanced["signals"] = _normalize_situation_signals(
        llm_signals,
        situation_id=situation_id,
        context=context,
        signal_template=signal_template,
    )
    if not enhanced["signals"]:
        raise LLMJsonValidationAbort(
            stage="situation_enhance_prompt",
            reason="`signals` failed normalization after enhance response",
            raw_output=json.dumps(enhanced, ensure_ascii=False),
        )
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
