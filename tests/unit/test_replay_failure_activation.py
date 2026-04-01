from omen.simulation.replay import compare_run_results


def _base_result(adoption_resistance: float) -> dict:
    return {
        "run_id": "run-base",
        "outcome_class": "convergence",
        "winner": {"actor_id": "a", "user_edge_count": 10},
        "final_competition_edges": [["a", "b"]],
        "snapshots": [{"step": 1}],
        "ontology_setup": {
            "applied_axioms": {
                "activation": ["AX-1"],
                "propagation": ["AX-2"],
                "counterfactual": ["AX-3"],
            },
            "space_summary": {
                "adoption_resistance": adoption_resistance,
            },
        },
    }


def test_compare_run_results_failure_activation_triggers_on_high_resistance() -> None:
    baseline = _base_result(0.4)
    variation = _base_result(0.8)

    comparison = compare_run_results(baseline, variation)

    failure_activation = comparison["failure_activation"]
    assert failure_activation["rules"]
    assert failure_activation["triggered"] is True
    assert "AX-3" in failure_activation["triggered_rule_ids"]


def test_compare_run_results_failure_activation_not_triggered_on_low_resistance() -> None:
    baseline = _base_result(0.4)
    variation = _base_result(0.5)

    comparison = compare_run_results(baseline, variation)

    failure_activation = comparison["failure_activation"]
    assert failure_activation["rules"]
    assert failure_activation["triggered"] is False
    assert failure_activation["triggered_rule_ids"] == []
