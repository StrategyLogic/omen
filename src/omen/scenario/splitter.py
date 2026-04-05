"""Normalize LLM-generated scenarios into fixed deterministic A/B/C slot intents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScenarioSlotPolicy:
    key: str
    label: str
    intent: str
    signal_basis: str
    objective: str
    tradeoffs: tuple[str, str]
    resistance: tuple[float, float, float, float]
    constraint_hint: str


def fixed_slot_policies() -> tuple[ScenarioSlotPolicy, ...]:
    """Return canonical A/B/C generation policies for deterministic scenario splitting."""
    return (
        ScenarioSlotPolicy(
            key="A",
            label="Aggressive/Alternative",
            intent="Challenger strategy",
            signal_basis="Optimistic assumptions from positive signal chain",
            objective="Seize strategic initiative via accelerated challenger moves.",
            tradeoffs=(
                "Execution speed vs operating stability",
                "Aggressive investment vs short-term margin protection",
            ),
            resistance=(0.8, 0.7, 0.6, 0.7),
            constraint_hint="Prioritize upside signal capture while controlling execution fragility",
        ),
        ScenarioSlotPolicy(
            key="B",
            label="Baseline/Conservative",
            intent="Maintainer strategy",
            signal_basis="Linear extrapolation from current state",
            objective="Preserve continuity while improving baseline efficiency.",
            tradeoffs=(
                "Predictability vs innovation velocity",
                "Cost control vs option creation",
            ),
            resistance=(0.5, 0.5, 0.5, 0.4),
            constraint_hint="Prioritize continuity under linearly projected market and org constraints",
        ),
        ScenarioSlotPolicy(
            key="C",
            label="Collapse/Contingency",
            intent="Extreme-risk strategy",
            signal_basis="Negative signal breakout and downside cascade",
            objective="Protect survivability under downside shock conditions.",
            tradeoffs=(
                "Emergency containment vs long-term autonomy",
                "Fast de-risking vs strategic upside preservation",
            ),
            resistance=(0.4, 0.4, 0.5, 0.3),
            constraint_hint="Prioritize downside containment and contingency optionality",
        ),
    )


def normalize_llm_scenarios_with_policy(
    llm_scenarios: list[Any],
    *,
    source_hint: str,
) -> list[dict[str, Any]]:
    """Normalize LLM output to strict A/B/C semantics without local hard splitting."""
    policies = fixed_slot_policies()
    by_key: dict[str, dict[str, Any]] = {}
    slot_order = [slot.key for slot in policies]

    for index, item in enumerate(llm_scenarios):
        if isinstance(item, dict):
            key = str(item.get("scenario_key") or "").strip().upper()
            if key in {"A", "B", "C"}:
                by_key[key] = item
                continue
            if index < len(slot_order):
                by_key.setdefault(slot_order[index], item)
            continue

        text = str(item).strip()
        if not text:
            continue
        if index < len(slot_order):
            by_key.setdefault(
                slot_order[index],
                {
                    "scenario_key": slot_order[index],
                    "title": f"Scenario {slot_order[index]}",
                    "objective": text,
                    "constraints": [text],
                    "tradeoff_pressure": [],
                    "variables": [],
                    "resistance_assumptions": {},
                    "modeling_notes": ["Derived from plain-text LLM scenario payload"],
                },
            )

    missing = [slot.key for slot in policies if slot.key not in by_key]
    if missing:
        raise ValueError(f"LLM scenario decomposition missing required slots: {missing}")

    normalized: list[dict[str, Any]] = []
    for policy in policies:
        raw = by_key[policy.key]
        constraints = [str(x).strip() for x in (raw.get("constraints") or []) if str(x).strip()]
        if not constraints:
            constraints = [policy.constraint_hint]

        tradeoffs = [str(x).strip() for x in (raw.get("tradeoff_pressure") or []) if str(x).strip()]
        if not tradeoffs:
            tradeoffs = list(policy.tradeoffs)

        variables = raw.get("variables") or []
        if not isinstance(variables, list) or not variables:
            variables = [
                {
                    "name": "signal_direction",
                    "type": "categorical",
                    "value_range_or_enum": ["positive", "neutral", "negative"],
                    "baseline_assumption": policy.signal_basis,
                    "rationale": "Policy-guided fallback variable after LLM normalization",
                    "signal_ref": f"signal::{policy.key.lower()}::primary",
                    "constraint_ref": "market::primary",
                }
            ]

        resistance = raw.get("resistance_assumptions") or {}
        default_r = policy.resistance
        normalized.append(
            {
                "scenario_key": policy.key,
                "title": str(raw.get("title") or f"Scenario {policy.key}: {policy.label}").strip(),
                "goal": str(raw.get("goal") or policy.objective).strip(),
                "target": str(raw.get("target") or "strategic-position").strip(),
                "objective": str(raw.get("objective") or policy.objective).strip(),
                "variables": variables,
                "constraints": constraints,
                "tradeoff_pressure": tradeoffs,
                "resistance_assumptions": {
                    "structural_conflict": float(resistance.get("structural_conflict", default_r[0])),
                    "resource_reallocation_drag": float(resistance.get("resource_reallocation_drag", default_r[1])),
                    "cultural_misalignment": float(resistance.get("cultural_misalignment", default_r[2])),
                    "veto_node_intensity": float(resistance.get("veto_node_intensity", default_r[3])),
                    "aggregate_resistance": float(
                        resistance.get("aggregate_resistance", round(sum(default_r) / 4.0, 3))
                    ),
                    "assumption_rationale": [
                        *[
                            str(x).strip()
                            for x in (resistance.get("assumption_rationale") or [])
                            if str(x).strip()
                        ],
                        source_hint,
                        f"intent: {policy.intent}",
                    ],
                },
                "modeling_notes": [
                    *[
                        str(x).strip()
                        for x in (raw.get("modeling_notes") or [])
                        if str(x).strip()
                    ],
                    "Scenario normalized under deterministic A/B/C intent policy",
                    f"signal_basis: {policy.signal_basis}",
                ],
            }
        )
    return normalized
