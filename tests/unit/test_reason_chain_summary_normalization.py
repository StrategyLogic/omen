from omen.simulation.reason import _normalize_llm_reason_chain


def test_reason_chain_summary_not_placeholder_and_within_word_limit() -> None:
    chain = {
        "steps": [
            {
                "step_id": "step_1",
                "step_type": "seed_inference",
                "summary": "seed_inference",
                "inputs": ["scenario.variables", "planning_query.signals"],
                "outputs": {
                    "tech_space_seed": [{"dimension": "capability_frontier_shift"}],
                    "market_space_seed": [{"dimension": "ecosystem_lockin"}],
                },
            }
        ],
        "conclusions": {"required": [], "warning": [], "blocking": []},
    }

    normalized = _normalize_llm_reason_chain(chain)

    assert normalized is not None
    summary = str(normalized["steps"][0].get("summary") or "")
    assert summary
    assert summary != "seed_inference"
    assert len(summary.split()) <= 100
