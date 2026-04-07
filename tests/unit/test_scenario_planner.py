from omen.scenario.planner import normalize_llm_scenarios_with_policy
from omen.scenario.space import build_planning_query
from omen.scenario.template_loader import load_planning_template


def test_normalize_llm_scenarios_rejects_plain_text_slots() -> None:
    try:
        normalize_llm_scenarios_with_policy(
            ["A", "B", "C"],
            source_hint="Derived from situation artifact: sap_reltio_acquisition",
        )
    except ValueError as exc:
        assert "non-object payload" in str(exc)
    else:
        raise AssertionError("Expected ValueError for plain-text LLM scenario payload")


def test_normalize_llm_scenarios_rejects_incomplete_structured_slots() -> None:
    try:
        normalize_llm_scenarios_with_policy(
            [
                {"scenario_key": "A", "title": "A", "objective": "oA"},
                {"scenario_key": "B", "title": "B", "objective": "oB"},
                {"scenario_key": "C", "title": "C", "objective": "oC"},
            ],
            source_hint="Derived from situation artifact: sap_reltio_acquisition",
        )
    except ValueError as exc:
        assert "incomplete structured payload" in str(exc)
        assert "variables" in str(exc)
    else:
        raise AssertionError("Expected ValueError for incomplete structured scenario payload")


def test_build_planning_query_preserves_signal_mechanism_fields() -> None:
    template = load_planning_template()
    planning_query = build_planning_query(
        situation_artifact={
            "id": "sap_reltio_acquisition",
            "signals": [
                {
                    "signal_id": "signal.standardization_push",
                    "name": "hyperscaler-led data ecosystem standardization",
                    "domain": "standard",
                    "direction": "up",
                    "strength": 0.82,
                    "mechanism_note": "Standardization narrows integration tolerance and raises bundle pressure.",
                    "mapped_targets": [
                        {
                            "space": "market",
                            "element_key": "bundle-led displacement",
                            "impact_type": "driver",
                            "impact_strength": 0.8,
                            "mechanism_conditions": {
                                "expected_effect": "Increases suite displacement pressure.",
                                "activation_condition": "When governance buyers prioritize integrated stacks.",
                            },
                        }
                    ],
                    "cascade_rules": [
                        {
                            "trigger_condition": "If data stack governance centralizes",
                            "next_signal_id": "signal.bundle_procurement",
                            "expected_lag": "mid",
                        }
                    ],
                    "market_constraints": [
                        {
                            "constraint_key": "governance-led procurement concentration",
                            "binding_strength": 0.78,
                        }
                    ],
                }
            ],
            "context": {"hard_constraints": ["cash runway", "ecosystem inertia"]},
        },
        actor_ref="actors/steve-jobs.md",
        template=template,
    )

    signal_input = planning_query["space_inputs"][0]
    assert signal_input["signal_id"] == "signal.standardization_push"
    assert signal_input["domain"] == "standard"
    assert signal_input["direction"] == "up"
    assert signal_input["strength"] == 0.82
    assert signal_input["mapped_targets"][0]["element_key"] == "bundle-led displacement"
    assert signal_input["cascade_rules"][0]["next_signal_id"] == "signal.bundle_procurement"
    assert signal_input["market_constraints"][0]["constraint_key"] == "governance-led procurement concentration"