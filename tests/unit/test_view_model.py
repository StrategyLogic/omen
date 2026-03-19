from omen.ui.view_model import build_case_replay_view_model


def test_view_model_nodes_include_business_events() -> None:
    result = {
        "outcome_class": "convergence",
        "known_outcome": "project failed in market expansion",
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
    assert view_model["reality_graph_nodes"]
    reality_node_ids = {node["id"] for node in view_model["reality_graph_nodes"]}
    assert "real-gap-1" in reality_node_ids
    assert "real-end" in reality_node_ids
    assert view_model["reality_graph_edges"]
    assert len(view_model["reality_graph_edges"]) >= 2
