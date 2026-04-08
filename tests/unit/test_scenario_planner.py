from pathlib import Path
import json

import pytest

from omen.scenario.planner import normalize_llm_scenarios_with_policy
from omen.scenario.planner import plan_scenarios_from_situation
from omen.scenario.space import build_planning_query
from omen.scenario.planner import load_planning_template


def test_normalize_llm_scenarios_accepts_plain_text_slots_with_fallback_by_default() -> None:
    with pytest.raises(ValueError, match="must return JSON objects"):
        normalize_llm_scenarios_with_policy(
            ["A", "B", "C"],
            source_hint="Derived from situation artifact: sap_reltio_acquisition",
        )


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
    with pytest.raises(ValueError, match="empty variables"):
        normalize_llm_scenarios_with_policy(
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

    actor_path = tmp_path / "actor_ontology.json"
    actor_path.write_text(
        json.dumps(
            {
                "actors": [
                    {
                        "type": "StrategicActor",
                        "name": "SAP",
                        "role": "enterprise software vendor",
                        "profile": {
                            "strategic_style": {
                                "decision_style": "platform expansion",
                                "value_proposition": "integrated enterprise stack",
                                "decision_preferences": ["ecosystem leverage"],
                                "non_negotiables": ["portfolio coherence"],
                            }
                        },
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
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
            actor_ref=str(actor_path),
            config_path="config/llm.toml",
            traces_dir=traces_dir,
        )

    assert not traces_dir.exists()


def test_build_planning_query_uses_actor_style_weighted_similarity_scores(tmp_path: Path) -> None:
    actor_path = tmp_path / "actor_ontology.json"
    actor_path.write_text(
        json.dumps(
            {
                "actors": [
                    {
                        "type": "StrategicActor",
                        "profile": {
                            "strategic_style": {
                                "decision_style": "Aggressive growth and proactive competition",
                                "value_proposition": "Expand through bold product bets",
                                "decision_preferences": ["high speed", "offensive positioning"],
                                "non_negotiables": ["win key rival battles"],
                            }
                        },
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    template = load_planning_template()
    planning_query = build_planning_query(
        situation_artifact={
            "id": "sap_reltio_acquisition",
            "signals": [{"name": "ecosystem pressure", "strength": 0.7}],
            "context": {"hard_constraints": []},
        },
        actor_ref=str(actor_path),
        template=template,
    )

    similarity = {item["scenario_key"]: item for item in planning_query["similarity_scores"]}
    assert similarity["A"]["source"] == "planning_template_default"
    assert abs(sum(float(item["score"]) for item in similarity.values()) - 1.0) < 1e-6


def test_plan_scenarios_enhances_inadmissible_actor_profile_before_planning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor_path = tmp_path / "actor_ontology.json"
    actor_path.write_text(
        json.dumps(
            {
                "actors": [
                    {
                        "type": "StrategicActor",
                        "profile": {
                            "strategic_style": {
                                "decision_style": "",
                                "value_proposition": "",
                                "decision_preferences": [],
                                "non_negotiables": [],
                            }
                        },
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "omen.scenario.planner.decompose_scenario_from_situation",
        lambda **kwargs: {
            "pack_id": kwargs["pack_id"],
            "pack_version": kwargs["pack_version"],
            "derived_from_situation_id": "sap_reltio_acquisition",
            "ontology_version": "scenario_ontology_v1",
            "scenarios": [
                {
                    "scenario_key": "A",
                    "title": "A",
                    "goal": "gA",
                    "target": "tA",
                    "objective": "oA",
                    "variables": [{"name": "vA"}],
                    "constraints": ["cA"],
                    "tradeoff_pressure": ["tpA"],
                },
                {
                    "scenario_key": "B",
                    "title": "B",
                    "goal": "gB",
                    "target": "tB",
                    "objective": "oB",
                    "variables": [{"name": "vB"}],
                    "constraints": ["cB"],
                    "tradeoff_pressure": ["tpB"],
                },
                {
                    "scenario_key": "C",
                    "title": "C",
                    "goal": "gC",
                    "target": "tC",
                    "objective": "oC",
                    "variables": [{"name": "vC"}],
                    "constraints": ["cC"],
                    "tradeoff_pressure": ["tpC"],
                },
            ],
        },
    )

    monkeypatch.setattr(
        "omen.analysis.actor.formation.invoke_text_prompt",
        lambda **kwargs: json.dumps(
            {
                "decision_style": "Balanced and deliberate",
                "value_proposition": "Durable compounding",
                "decision_preferences": ["quality execution"],
                "non_negotiables": ["strategic coherence"],
            },
            ensure_ascii=False,
        ),
    )

    monkeypatch.setattr(
        "omen.scenario.prior.invoke_text_prompt",
        lambda **kwargs: json.dumps(
            {
                "raw_prior_scores": [
                    {"scenario_key": "A", "score": 0.2, "explain": "A path explanation"},
                    {"scenario_key": "B", "score": 0.55, "explain": "B path explanation"},
                    {"scenario_key": "C", "score": 0.25, "explain": "C path explanation"},
                ]
            },
            ensure_ascii=False,
        ),
    )

    traces_dir = tmp_path / "traces"
    plan_scenarios_from_situation(
        situation_artifact={
            "id": "sap_reltio_acquisition",
            "signals": [{"name": "signal", "strength": 0.6}],
            "context": {"hard_constraints": []},
        },
        pack_id="sap_v1",
        pack_version="1.0.0",
        actor_ref=str(actor_path),
        config_path="config/llm.toml",
        traces_dir=traces_dir,
    )

    refreshed = json.loads(actor_path.read_text(encoding="utf-8"))
    style = refreshed["actors"][0]["profile"]["strategic_style"]
    assert style["decision_style"] == "Balanced and deliberate"
    assert style["value_proposition"] == "Durable compounding"
    assert style["decision_preferences"] == ["quality execution"]
    assert style["non_negotiables"] == ["strategic coherence"]


def test_plan_scenarios_uses_llm_prior_scores_with_explanations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor_path = tmp_path / "actor_ontology.json"
    actor_path.write_text(
        json.dumps(
            {
                "actors": [
                    {
                        "type": "StrategicActor",
                        "name": "SAP",
                        "role": "enterprise software vendor",
                        "profile": {
                            "strategic_style": {
                                "decision_style": "platform expansion",
                                "value_proposition": "integrated enterprise stack",
                                "decision_preferences": ["ecosystem leverage"],
                                "non_negotiables": ["portfolio coherence"],
                            }
                        },
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "omen.scenario.planner.decompose_scenario_from_situation",
        lambda **kwargs: {
            "pack_id": kwargs["pack_id"],
            "pack_version": kwargs["pack_version"],
            "derived_from_situation_id": "sap_reltio_acquisition",
            "ontology_version": "scenario_ontology_v1",
            "scenarios": [
                {
                    "scenario_key": "A",
                    "title": "A",
                    "goal": "gA",
                    "target": "tA",
                    "objective": "oA",
                    "variables": [{"name": "vA"}],
                    "constraints": ["cA"],
                    "tradeoff_pressure": ["tpA"],
                },
                {
                    "scenario_key": "B",
                    "title": "B",
                    "goal": "gB",
                    "target": "tB",
                    "objective": "oB",
                    "variables": [{"name": "vB"}],
                    "constraints": ["cB"],
                    "tradeoff_pressure": ["tpB"],
                },
                {
                    "scenario_key": "C",
                    "title": "C",
                    "goal": "gC",
                    "target": "tC",
                    "objective": "oC",
                    "variables": [{"name": "vC"}],
                    "constraints": ["cC"],
                    "tradeoff_pressure": ["tpC"],
                },
            ],
        },
    )

    monkeypatch.setattr(
        "omen.scenario.prior.invoke_text_prompt",
        lambda **kwargs: json.dumps(
            {
                "raw_prior_scores": [
                    {"scenario_key": "A", "score": 0.2, "explain": "Style less aligned with offense path"},
                    {"scenario_key": "B", "score": 0.55, "explain": "Style prefers stability and integration defense"},
                    {"scenario_key": "C", "score": 0.25, "explain": "Some rivalry response pressure exists"},
                ]
            },
            ensure_ascii=False,
        ),
    )

    traces_dir = tmp_path / "traces"
    plan_scenarios_from_situation(
        situation_artifact={
            "id": "sap_reltio_acquisition",
            "signals": [{"name": "signal", "strength": 0.6}],
            "context": {"hard_constraints": []},
        },
        pack_id="sap_v1",
        pack_version="1.0.0",
        actor_ref=str(actor_path),
        config_path="config/llm.toml",
        traces_dir=traces_dir,
    )

    prior_snapshot = json.loads((traces_dir / "prior_snapshot.json").read_text(encoding="utf-8"))
    raw = {item["scenario_key"]: item for item in prior_snapshot["raw_prior_scores"]}
    normalized = {item["scenario_key"]: item for item in prior_snapshot["normalized_priors"]}

    assert raw["B"]["score"] == 0.55
    assert "stability" in raw["B"]["explain"]
    assert "rivalry" in raw["C"]["explain"]
    assert abs(sum(float(item["score"]) for item in normalized.values()) - 1.0) < 1e-6
    assert all(str(item.get("explain") or "").strip() for item in normalized.values())