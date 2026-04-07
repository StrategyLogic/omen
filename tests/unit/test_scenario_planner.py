from pathlib import Path

import pytest

from omen.scenario.planner import normalize_llm_scenarios_with_policy
from omen.scenario.planner import plan_scenarios_from_situation
from omen.scenario.space import build_planning_query
from omen.scenario.template_loader import load_planning_template


def test_normalize_llm_scenarios_accepts_plain_text_slots_with_fallback_by_default() -> None:
    payload = normalize_llm_scenarios_with_policy(
        ["A", "B", "C"],
        source_hint="Derived from situation artifact: sap_reltio_acquisition",
    )

    assert [item["scenario_key"] for item in payload] == ["A", "B", "C"]
    assert payload[0]["objective"] == "A"
    assert payload[0]["constraints"] == ["A"]
    assert payload[0]["modeling_notes"]


def test_normalize_llm_scenarios_rejects_incomplete_structured_slots_in_strict_mode() -> None:
    try:
        normalize_llm_scenarios_with_policy(
            [
                {"scenario_key": "A", "title": "A", "objective": "oA"},
                {"scenario_key": "B", "title": "B", "objective": "oB"},
                {"scenario_key": "C", "title": "C", "objective": "oC"},
            ],
            source_hint="Derived from situation artifact: sap_reltio_acquisition",
            strict_structured=True,
        )
    except ValueError as exc:
        assert "incomplete structured payload" in str(exc)
        assert "variables" in str(exc)
    else:
        raise AssertionError("Expected ValueError for incomplete structured scenario payload")


def test_normalize_llm_scenarios_rejects_plain_text_slots_in_strict_mode() -> None:
    try:
        normalize_llm_scenarios_with_policy(
            ["A", "B", "C"],
            source_hint="Derived from situation artifact: sap_reltio_acquisition",
            strict_structured=True,
        )
    except ValueError as exc:
        assert "non-object payload" in str(exc)
    else:
        raise AssertionError("Expected ValueError for plain-text LLM scenario payload")


def test_normalize_llm_scenarios_normalizes_variable_and_resistance_text_types() -> None:
    payload = normalize_llm_scenarios_with_policy(
        [
            {
                "scenario_key": "A",
                "title": "A",
                "goal": "gA",
                "target": "tA",
                "objective": "oA",
                "variables": ["market adoption"],
                "constraints": ["cA"],
                "tradeoff_pressure": "speed vs quality",
                "resistance_assumptions": "legacy stack inertia",
                "modeling_notes": ["note A"],
            },
            {
                "scenario_key": "B",
                "title": "B",
                "goal": "gB",
                "target": "tB",
                "objective": "oB",
                "variables": [{"name": "risk"}],
                "constraints": ["cB"],
                "tradeoff_pressure": ["cost vs speed"],
                "resistance_assumptions": {},
                "modeling_notes": ["note B"],
            },
            {
                "scenario_key": "C",
                "title": "C",
                "goal": "gC",
                "target": "tC",
                "objective": "oC",
                "variables": [{"name": "rival intensity"}],
                "constraints": ["cC"],
                "tradeoff_pressure": ["defense vs growth"],
                "resistance_assumptions": {},
                "modeling_notes": ["note C"],
            },
        ],
        source_hint="Derived from situation artifact: sap_reltio_acquisition",
    )

    scenario_a = payload[0]
    assert isinstance(scenario_a["variables"], list)
    assert isinstance(scenario_a["variables"][0], dict)
    assert scenario_a["tradeoff_pressure"] == ["speed vs quality"]
    assert "legacy stack inertia" in scenario_a["resistance_assumptions"]["assumption_rationale"]


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


def test_plan_scenarios_aborts_without_writing_artifacts_on_invalid_decomposition_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "omen.scenario.planner.decompose_scenario_from_situation",
        lambda **kwargs: {
            "pack_id": kwargs["pack_id"],
            "pack_version": kwargs["pack_version"],
            "derived_from_situation_id": "sap_reltio_acquisition",
            "ontology_version": "scenario_ontology_v1",
            "scenarios": "A",
        },
    )

    traces_dir = tmp_path / "traces"
    with pytest.raises(ValueError, match="Scenario decomposition validation failed"):
        plan_scenarios_from_situation(
            situation_artifact={
                "id": "sap_reltio_acquisition",
                "signals": [
                    {
                        "id": "sig-1",
                        "name": "signal",
                        "domain": "market",
                        "strength": 0.6,
                        "direction": "up",
                        "mapped_targets": [
                            {
                                "space": "MarketSpace",
                                "element_key": "demand_shift",
                                "impact_type": "driver",
                                "impact_strength": 0.7,
                                "mechanism_conditions": {
                                    "activation_condition": "always",
                                    "expected_effect": "supports demand",
                                },
                            }
                        ],
                        "cascade_rules": [],
                        "no_cascade_reason": "direct effect",
                        "market_constraints": [
                            {
                                "constraint_key": "procurement_friction",
                                "binding_strength": 0.5,
                            }
                        ],
                        "mechanism_note": "test",
                    }
                ],
                "context": {"hard_constraints": ["procurement_friction"]},
            },
            pack_id="sap_v1",
            pack_version="1.0.0",
            actor_ref="actors/steve-jobs.md",
            config_path="config/llm.toml",
            traces_dir=traces_dir,
        )

    assert not traces_dir.exists()