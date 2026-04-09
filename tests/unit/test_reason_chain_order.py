from omen.analysis.actor.derivation_trace import reasoning_order_is_valid


def test_reason_chain_order_accepts_seed_to_blocking_sequence() -> None:
    assert reasoning_order_is_valid(
        [
            "seed",
            "constraint_activation",
            "target_or_objective",
            "gap",
            "required_or_warning_or_blocking",
        ]
    )


def test_reason_chain_order_rejects_gap_before_target() -> None:
    assert not reasoning_order_is_valid(
        [
            "seed",
            "constraint_activation",
            "gap",
            "target_or_objective",
            "required_or_warning_or_blocking",
        ]
    )
