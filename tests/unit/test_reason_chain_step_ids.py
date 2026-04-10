from omen.simulation.reason import (
    build_hierarchical_step_id,
    is_hierarchical_step_id,
    validate_reason_chain_step_ids,
)


def test_reason_chain_step_id_generator_and_pattern() -> None:
    assert build_hierarchical_step_id(1, 1) == "step_1.1"
    assert build_hierarchical_step_id(2, 1) == "step_2.1"
    assert is_hierarchical_step_id("step_1.1")
    assert is_hierarchical_step_id("step_2.1")
    assert is_hierarchical_step_id("step_1")
    assert is_hierarchical_step_id("seed_step")
    assert not is_hierarchical_step_id("")


def test_reason_chain_step_id_validation_for_step_objects() -> None:
    assert validate_reason_chain_step_ids(
        [
            {"step_id": "step_1.1"},
            {"step_id": "step_2.1"},
        ]
    )
    assert not validate_reason_chain_step_ids(
        [
            {"step_id": ""},
            {"step_id": "step_2.1"},
        ]
    )
