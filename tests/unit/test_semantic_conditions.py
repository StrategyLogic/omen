from omen.simulation.condition_types import normalize_semantic_conditions


def test_normalize_semantic_conditions_assigns_categories() -> None:
    conditions = [
        {
            "type": "override",
            "key": "user_overlap_threshold",
            "value": 0.9,
            "description": "override `user_overlap_threshold` -> 0.9",
        },
        {
            "type": "budget_delta",
            "actor_id": "ai-memory",
            "delta": 200,
            "description": "budget shock",
        },
    ]

    normalized = normalize_semantic_conditions(conditions)

    assert normalized[0]["semantic_type"] == "overlap_threshold_change"
    assert normalized[0]["category"] == "threshold_adjustment"
    assert normalized[1]["semantic_type"] == "budget_shock"
    assert normalized[1]["category"] == "resource_shock"
