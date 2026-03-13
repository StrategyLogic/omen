from omen.simulation.precision_metrics import (
    evaluate_directional_correctness,
    evaluate_repeatability,
    evaluate_trace_completeness,
)


def test_evaluate_repeatability_counts_dominant_outcome_and_drivers() -> None:
    results = [
        {"outcome_class": "replacement", "top_drivers": ["a", "b", "c"]},
        {"outcome_class": "replacement", "top_drivers": ["a", "b", "c"]},
        {"outcome_class": "coexistence", "top_drivers": ["a", "x", "c"]},
    ]

    metrics = evaluate_repeatability(results)

    assert metrics["run_count"] == 3
    assert metrics["dominant_outcome_class"] == "replacement"
    assert metrics["outcome_consistency"] == 2 / 3
    assert metrics["dominant_top_drivers"] == ["a", "b", "c"]
    assert metrics["top_driver_consistency"] == 2 / 3


def test_evaluate_directional_correctness_uses_semantic_conditions() -> None:
    comparison = {
        "deltas": [
            {"metric": "winner_user_edge_count", "delta": 8},
            {"metric": "competition_edge_count", "delta": 2},
        ]
    }
    conditions = [
        {"type": "budget_delta", "semantic_type": "budget_shock", "delta": 100},
        {"type": "override", "semantic_type": "overlap_threshold_change"},
    ]

    metrics = evaluate_directional_correctness(comparison, conditions=conditions)

    assert metrics["total_checks"] == 2
    assert metrics["matched_checks"] == 2
    assert metrics["directional_correctness"] == 1.0


def test_evaluate_trace_completeness_requires_all_trace_components() -> None:
    links = [
        {
            "condition_refs": ["c1"],
            "rule_chain_refs": ["r1"],
            "evidence_refs": ["e1"],
        },
        {
            "condition_refs": ["c2"],
            "rule_chain_refs": [],
            "evidence_refs": ["e2"],
        },
    ]

    metrics = evaluate_trace_completeness(links)

    assert metrics["total_links"] == 2
    assert metrics["complete_links"] == 1
    assert metrics["trace_completeness"] == 0.5
