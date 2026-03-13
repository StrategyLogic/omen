"""Precision governance report serializers."""

from __future__ import annotations

from typing import Any


def build_precision_report(
    *,
    gate_evaluation: dict[str, Any],
    profile_payload: dict[str, Any],
    precision_payload: dict[str, Any] | None = None,
    comparison_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "governance": {
            "profile": {
                "profile_id": profile_payload.get("profile_id"),
                "case_id": profile_payload.get("case_id"),
                "status": profile_payload.get("status"),
            },
            "gate_evaluation": gate_evaluation,
        },
        "evidence": {
            "repeatability": (precision_payload or {}).get("repeatability", {}),
            "directional_correctness": ((comparison_payload or {}).get("precision_summary", {}) or {}).get(
                "directional_correctness", {}
            ),
            "trace_completeness": ((comparison_payload or {}).get("precision_summary", {}) or {}).get(
                "trace_completeness", {}
            ),
        },
    }
