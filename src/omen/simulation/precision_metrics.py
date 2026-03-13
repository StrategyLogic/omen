"""Precision evaluation metrics for Spec 4.

These helpers keep evaluation deterministic and lightweight, so they can be
used in CLI flows and tests without adding external dependencies.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


def evaluate_repeatability(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate consistency for repeated runs of the same scenario."""

    if not results:
        return {
            "run_count": 0,
            "outcome_consistency": 0.0,
            "top_driver_consistency": 0.0,
            "dominant_outcome_class": None,
            "dominant_top_drivers": [],
        }

    outcome_classes = [str(result.get("outcome_class")) for result in results]
    outcome_counter = Counter(outcome_classes)
    dominant_outcome, dominant_outcome_count = outcome_counter.most_common(1)[0]

    top_driver_sets = [tuple(result.get("top_drivers", [])[:3]) for result in results]
    driver_counter = Counter(top_driver_sets)
    dominant_drivers, dominant_driver_count = driver_counter.most_common(1)[0]

    run_count = len(results)
    return {
        "run_count": run_count,
        "outcome_consistency": dominant_outcome_count / run_count,
        "top_driver_consistency": dominant_driver_count / run_count,
        "dominant_outcome_class": dominant_outcome,
        "dominant_top_drivers": list(dominant_drivers),
    }


def evaluate_directional_correctness(
    comparison: dict[str, Any],
    *,
    conditions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate expected direction checks for known semantic condition types."""

    raw_conditions: Any = conditions if conditions is not None else comparison.get("conditions", [])
    normalized_conditions: list[dict[str, Any]]
    if isinstance(raw_conditions, list):
        normalized_conditions = [item for item in raw_conditions if isinstance(item, dict)]
    else:
        normalized_conditions = []

    deltas_by_metric = {
        str(delta.get("metric")): float(delta.get("delta", 0.0))
        for delta in comparison.get("deltas", [])
    }

    checks: list[dict[str, Any]] = []
    for condition in normalized_conditions:
        semantic_type = str(condition.get("semantic_type", ""))
        condition_type = str(condition.get("type", ""))

        if semantic_type == "budget_shock" or condition_type == "budget_delta":
            budget_delta = float(condition.get("delta", 0.0))
            observed = deltas_by_metric.get("winner_user_edge_count", 0.0)
            expected_sign = 1 if budget_delta >= 0 else -1
            matched = observed == 0.0 or (observed > 0 and expected_sign > 0) or (observed < 0 and expected_sign < 0)
            checks.append(
                {
                    "condition": semantic_type or condition_type,
                    "metric": "winner_user_edge_count",
                    "expected_direction": "increase" if expected_sign > 0 else "decrease",
                    "observed_delta": observed,
                    "matched": matched,
                }
            )

        if semantic_type == "overlap_threshold_change":
            observed = deltas_by_metric.get("competition_edge_count", 0.0)
            checks.append(
                {
                    "condition": semantic_type,
                    "metric": "competition_edge_count",
                    "expected_direction": "non_negative_change",
                    "observed_delta": observed,
                    "matched": observed >= 0,
                }
            )

    total = len(checks)
    matched_count = sum(1 for check in checks if check.get("matched"))
    return {
        "total_checks": total,
        "matched_checks": matched_count,
        "directional_correctness": (matched_count / total) if total else 1.0,
        "checks": checks,
    }


def evaluate_trace_completeness(outcome_evidence_links: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate condition→rule→evidence trace completeness across links."""

    if not outcome_evidence_links:
        return {
            "total_links": 0,
            "complete_links": 0,
            "trace_completeness": 0.0,
        }

    complete = 0
    for link in outcome_evidence_links:
        has_conditions = bool(link.get("condition_refs"))
        has_rules = bool(link.get("rule_chain_refs"))
        has_evidence = bool(link.get("evidence_refs"))
        if has_conditions and has_rules and has_evidence:
            complete += 1

    total = len(outcome_evidence_links)
    return {
        "total_links": total,
        "complete_links": complete,
        "trace_completeness": complete / total,
    }
