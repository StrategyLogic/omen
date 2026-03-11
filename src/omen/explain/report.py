"""Explanation report utilities (initial stub)."""

from __future__ import annotations


def build_explanation_stub(result: dict) -> dict:
    return {
        "run_id": result.get("run_id"),
        "branch_points": [],
        "causal_chain": [
            "functional_similarity increased",
            "user_overlap crossed threshold",
            "competition edges were activated",
        ],
    }
