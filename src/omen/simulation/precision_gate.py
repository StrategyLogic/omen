"""Precision gate evaluation against configured thresholds."""

from __future__ import annotations

from typing import Any

from omen.ingest.models import PrecisionEvaluationProfile


def _gate_result(name: str, observed: float, threshold: float) -> dict[str, Any]:
    passed = observed >= threshold
    return {
        "gate": name,
        "observed": observed,
        "threshold": threshold,
        "passed": passed,
    }


def evaluate_precision_gates(
    profile: PrecisionEvaluationProfile,
    *,
    repeatability_metrics: dict[str, Any] | None = None,
    directional_metrics: dict[str, Any] | None = None,
    trace_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repeatability_metrics = repeatability_metrics or {}
    directional_metrics = directional_metrics or {}
    trace_metrics = trace_metrics or {}

    outcome_consistency = float(repeatability_metrics.get("outcome_consistency", 0.0))
    top_driver_consistency = float(repeatability_metrics.get("top_driver_consistency", 0.0))
    repeatability_observed = min(outcome_consistency, top_driver_consistency)

    directional_observed = float(directional_metrics.get("directional_correctness", 0.0))
    trace_observed = float(trace_metrics.get("trace_completeness", 0.0))

    gates = [
        _gate_result("repeatability", repeatability_observed, profile.repeatability_threshold),
        _gate_result(
            "directional_correctness",
            directional_observed,
            profile.directional_correctness_threshold,
        ),
        _gate_result(
            "trace_completeness",
            trace_observed,
            profile.trace_completeness_threshold,
        ),
    ]

    failed = [gate for gate in gates if not gate["passed"]]
    return {
        "profile_id": profile.profile_id,
        "case_id": profile.case_id,
        "status": "passed" if not failed else "failed",
        "gates": gates,
        "failed_gate_count": len(failed),
        "remediation_targets": [
            f"increase {gate['gate']} from {gate['observed']:.3f} to >= {gate['threshold']:.3f}"
            for gate in failed
        ],
    }
