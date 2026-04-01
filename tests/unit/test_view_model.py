from omen.ui.view_model import build_case_replay_view_model


def test_view_model_nodes_include_business_events() -> None:
    result = {
        "outcome_class": "convergence",
        "ontology_setup": {
            "space_summary": {
                "tech_space_actor_count": 3,
                "market_space_actor_count": 2,
                "shared_actor_count": 2,
                "adoption_resistance": 0.7,
                "incumbent_response_speed": 0.6,
                "value_perception_gap": 0.5,
            }
        },
        "timeline": [
            {
                "step": 1,
                "competition_edges": [],
                "user_overlap": {"a:b": 0.0},
                "actors": {
                    "a": {"user_edge_count": 100},
                    "b": {"user_edge_count": 90},
                },
            },
            {
                "step": 2,
                "competition_edges": [],
                "user_overlap": {"a:b": 0.2},
                "actors": {
                    "a": {"user_edge_count": 102},
                    "b": {"user_edge_count": 95},
                },
            },
            {
                "step": 3,
                "competition_edges": [["a", "b"]],
                "user_overlap": {"a:b": 0.25},
                "actors": {
                    "a": {"user_edge_count": 103},
                    "b": {"user_edge_count": 101},
                },
            },
        ],
    }
    explanation = {
        "branch_points": [
            {"step": 1, "type": "user_overlap", "description": "overlap starts"},
            {"step": 2, "type": "competition_activation", "description": "competition starts"},
            {"step": 3, "type": "winner_emergence", "description": "winner emerges"},
        ],
        "reality_gap_analysis": [
            {
                "gap_id": "GAP-1",
                "factor": "simulated_vs_real_outcome",
                "reality_observation": "model diverges",
                "suggested_calibration": "recalibrate outcome mapping",
            },
            {
                "gap_id": "GAP-2",
                "factor": "adoption_resistance",
                "reality_observation": "high resistance",
                "suggested_calibration": "lower resistance",
            },
            {
                "gap_id": "GAP-3",
                "factor": "pilot_success_to_scale",
                "reality_observation": "pilot does not scale",
                "suggested_calibration": "model decision-chain friction",
            }
        ],
        "narrative_summary": "summary",
    }

    view_model = build_case_replay_view_model(result=result, explanation=explanation, case_id="demo")
    labels = [node["label"] for node in view_model["graph_nodes"]]
    summaries = [node["summary"] for node in view_model["graph_nodes"]]

    assert any("User overlap emerges" in label for label in labels)
    assert any("Competition activated" in label for label in labels)
    assert any("Adoption resistance" in label for label in labels)
    assert all("leader=" in summary for summary in summaries)
    assert view_model["space_summary"]["adoption_resistance"] == 0.7
    control_ids = {item["control_id"] for item in view_model["editable_controls"]}
    assert "adoption_resistance" in control_ids
    assert "incumbent_response_speed" in control_ids
    assert "value_perception_gap" in control_ids
    assert view_model["causal_gap_links"]
    assert view_model["gap_overlays"]
    assert {item["overlay_type"] for item in view_model["gap_overlays"]} == {"gap"}
    gap_sources = {item["source_node_id"] for item in view_model["gap_overlays"]}
    graph_node_ids = {node["id"] for node in view_model["graph_nodes"]}
    assert gap_sources.issubset(graph_node_ids)
    assert view_model["control_overlays"]
    assert {item["overlay_type"] for item in view_model["control_overlays"]} == {"control"}
    assert len(view_model["control_overlays"]) == len(view_model["editable_controls"])

    assert view_model["hypothesis_steps"]
    assert len(view_model["hypothesis_steps"]) == len(view_model["graph_nodes"])
    first_step = view_model["hypothesis_steps"][0]
    assert "state_vector" in first_step
    assert "hypotheses" in first_step

    transitions = view_model["weighted_transitions"]
    assert transitions
    assert len(transitions) == len(view_model["graph_edges"])
    for transition in transitions:
        assert 0.0 <= transition["baseline_weight"] <= 1.0
        assert 0.0 <= transition["adjusted_weight"] <= 1.0
        assert transition["driver_formula"]
        assert transition["prior_beta"]
        assert transition["calibrated_beta"]
        assert transition["sensitivity_analysis"]

    assert "edge_overrides" in view_model
    assert isinstance(view_model["edge_overrides"], list)
