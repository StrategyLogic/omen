from omen.simulation.control_mapper import map_control_to_overrides


def test_map_control_to_overrides_for_market_controls() -> None:
    assert map_control_to_overrides("adoption_resistance", 0.4) == {
        "ontology_setup.space_summary.adoption_resistance": 0.4
    }
    assert map_control_to_overrides("incumbent_response_speed", 0.7) == {
        "ontology_setup.space_summary.incumbent_response_speed": 0.7
    }
    assert map_control_to_overrides("value_perception_gap", 0.6) == {
        "ontology_setup.space_summary.value_perception_gap": 0.6
    }


def test_map_control_to_overrides_for_user_overlap_threshold() -> None:
    assert map_control_to_overrides("user_overlap_threshold", 0.3) == {
        "user_overlap_threshold": 0.3
    }
