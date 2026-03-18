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
    explanation = {"branch_points": [], "narrative_summary": "summary"}

    view_model = build_case_replay_view_model(result=result, explanation=explanation, case_id="demo")
    labels = [node["label"] for node in view_model["graph_nodes"]]
    summaries = [node["summary"] for node in view_model["graph_nodes"]]

    assert any("User overlap emerges" in label for label in labels)
    assert any("Competition activated" in label for label in labels)
    assert any("Adoption resistance" in label for label in labels)
    assert all("leader=" in summary for summary in summaries)
    assert view_model["space_summary"]["adoption_resistance"] == 0.7
