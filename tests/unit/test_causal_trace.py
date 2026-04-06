from omen.explain.causal_trace import extract_reality_gaps


def test_extract_reality_gaps_detects_outcome_mismatch() -> None:
    result = {
        "outcome_class": "convergence",
        "winner": {"actor_id": "x_developer_startup"},
        "ontology_setup": {"space_summary": {"adoption_resistance": 0.75}},
        "real_world_outcome": "market_entry_failure",
    }

    gaps = extract_reality_gaps(result)

    assert gaps
    assert any(gap["gap_id"] == "GAP-outcome-mismatch" for gap in gaps)
    assert any(gap["factor"] == "adoption_resistance" for gap in gaps)


def test_extract_reality_gaps_returns_empty_without_signals() -> None:
    result = {
        "outcome_class": "convergence",
        "winner": {"actor_id": "x_developer_startup"},
        "ontology_setup": {"space_summary": {"adoption_resistance": 0.3}},
        "real_world_outcome": "convergence",
    }

    gaps = extract_reality_gaps(result)

    assert not gaps