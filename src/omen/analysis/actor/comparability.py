"""Comparability helpers for deterministic strategic actor runs."""

from __future__ import annotations


def build_comparability_metadata(
    *,
    actor_profile_version: str,
    scenario_pack_version: str,
    calculation_policy_version: str,
    blocking_reasons: list[str] | None = None,
    executed_order: list[str] | None = None,
    required_order: tuple[str, ...] = ("A", "B", "C"),
) -> dict:
    reasons = list(blocking_reasons or [])
    if executed_order is not None:
        expected = list(required_order)
        if list(executed_order) != expected:
            reasons.append(
                f"scenario order mismatch: expected {expected}, got {list(executed_order)}"
            )
    return {
        "comparable": len(reasons) == 0,
        "blocking_reasons": reasons,
        "actor_profile_version": actor_profile_version,
        "scenario_pack_version": scenario_pack_version,
        "calculation_policy_version": calculation_policy_version,
    }
