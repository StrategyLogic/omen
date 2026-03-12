"""Helpers to build rule-trace references for explanation outputs."""

from __future__ import annotations

from typing import Any


def build_rule_trace_references(
    branch_points: list[dict[str, Any]],
    applied_axioms: dict[str, list[str]] | None,
) -> list[dict[str, Any]]:
    if not applied_axioms:
        return []

    references: list[dict[str, Any]] = []
    activation_ids = applied_axioms.get("activation", [])
    propagation_ids = applied_axioms.get("propagation", [])

    for point in branch_points:
        point_type = point.get("type")
        if point_type in {"user_overlap", "competition_activation"}:
            ids = activation_ids
        elif point_type == "winner_emergence":
            ids = propagation_ids
        else:
            ids = []

        for rule_id in ids:
            references.append(
                {
                    "rule_id": rule_id,
                    "branch_point_type": point_type,
                    "note": "rule linked by ontology reasoning profile",
                }
            )
    return references
