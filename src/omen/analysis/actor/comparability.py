"""Comparability helpers for deterministic strategic actor runs."""

from __future__ import annotations


def build_comparability_metadata(
    *,
    actor_profile_version: str,
    scenario_pack_version: str,
    calculation_policy_version: str,
    blocking_reasons: list[str] | None = None,
) -> dict:
    reasons = list(blocking_reasons or [])
    return {
        "comparable": len(reasons) == 0,
        "blocking_reasons": reasons,
        "actor_profile_version": actor_profile_version,
        "scenario_pack_version": scenario_pack_version,
        "calculation_policy_version": calculation_policy_version,
    }
