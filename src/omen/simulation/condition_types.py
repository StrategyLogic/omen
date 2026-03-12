"""Semantic condition typing helpers for compare outputs."""

from __future__ import annotations

from typing import Any


def _classify_override_key(key: str) -> tuple[str, str]:
    if key.endswith("user_overlap_threshold"):
        return "overlap_threshold_change", "threshold_adjustment"
    if key.endswith("budget"):
        return "budget_adjustment", "resource_shock"
    if "seed" in key:
        return "seed_change", "execution_control"
    return "parameter_override", "generic_override"


def to_semantic_condition(raw: dict[str, Any]) -> dict[str, Any]:
    condition_type = str(raw.get("type", "condition"))

    if condition_type == "override":
        key = str(raw.get("key", ""))
        typed_name, category = _classify_override_key(key)
        return {
            **raw,
            "semantic_type": typed_name,
            "category": category,
        }

    if condition_type == "budget_delta":
        return {
            **raw,
            "semantic_type": "budget_shock",
            "category": "resource_shock",
        }

    return {
        **raw,
        "semantic_type": condition_type,
        "category": raw.get("category", "generic_condition"),
    }


def normalize_semantic_conditions(conditions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [to_semantic_condition(condition) for condition in conditions]
