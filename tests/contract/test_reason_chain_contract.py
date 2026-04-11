import json
import sys
from pathlib import Path

from omen.simulation.reason import blocking_has_activation_links
from omen.cli.main import main
from omen.ingest.validators.scenario import validate_reason_chain_artifact_or_raise


def _mock_reason_chain_llm(*, config_path: str | None = None, user_prompt: str, system_prompt: str | None = None) -> str:
    _ = (config_path, user_prompt, system_prompt)
    if "Required keys: recommendation_summary, gap_summary, required_actions." in user_prompt:
        return json.dumps(
            {
                "recommendation_summary": "建议优先推进A路径，并以已激活约束作为节奏边界推进执行。",
                "gap_summary": "当前状态在约束激活下与目标达成之间仍存在执行闭环差距，需先打通关键前提再推进目标兑现。",
                "required_actions": "先完成阻断项对应前置动作并固化责任窗口，同时针对预警项建立周期性验证与纠偏机制。",
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "reason_chain": {
                "steps": [
                    {"step_id": "step_1.1", "step_type": "seed", "summary": "mock", "input_refs": ["scenario::A"]},
                    {"step_id": "step_2.1", "step_type": "constraint_activation", "summary": "mock", "input_refs": ["constraint::x"]},
                    {"step_id": "step_3.1", "step_type": "target_or_objective", "summary": "mock", "input_refs": ["objective::x"]},
                    {"step_id": "step_4.1", "step_type": "gap", "summary": "mock", "input_refs": ["scenario_conditions::warning"]},
                    {"step_id": "step_5.1", "step_type": "required_or_warning_or_blocking", "summary": "mock", "input_refs": ["scenario_conditions::blocking"]},
                ],
                "intermediate": {"dimension_mapping": [], "value_calculation": []},
                "conclusions": {
                    "required": [],
                    "warning": [],
                    "blocking": [
                        {
                            "text": "mock_blocking",
                            "activation_step_ids": ["step_2.1"],
                            "reason_step_ids": ["step_5.1"],
                        }
                    ],
                },
            }
        },
        ensure_ascii=False,
    )


def _write_ontology(path: Path) -> None:
    payload = {
        "pack_id": "strategic_actor_nokia_v1",
        "pack_version": "1.0.0",
        "derived_from_situation_id": "nokia-elop-2010",
        "ontology_version": "scenario_ontology_v1",
        "planning_query_ref": "traces/planning_query.json",
        "prior_snapshot_ref": "traces/prior_snapshot.json",
        "scenarios": [
            {
                "scenario_key": "A",
                "title": "A",
                "goal": "gA",
                "target": "tA",
                "objective": "oA",
                "variables": [{"name": "integration_standard_adoption_rate", "type": "categorical"}],
                "constraints": ["cA"],
                "tradeoff_pressure": ["tA"],
                "resistance_assumptions": {
                    "structural_conflict": 0.8,
                    "resource_reallocation_drag": 0.7,
                    "cultural_misalignment": 0.6,
                    "veto_node_intensity": 0.9,
                    "aggregate_resistance": 0.7,
                    "assumption_rationale": ["rA"],
                },
                "modeling_notes": ["nA"],
            },
            {
                "scenario_key": "B",
                "title": "B",
                "goal": "gB",
                "target": "tB",
                "objective": "oB",
                "variables": [{"name": "x", "type": "categorical"}],
                "constraints": ["cB"],
                "tradeoff_pressure": ["tB"],
                "resistance_assumptions": {
                    "structural_conflict": 0.5,
                    "resource_reallocation_drag": 0.5,
                    "cultural_misalignment": 0.5,
                    "veto_node_intensity": 0.4,
                    "aggregate_resistance": 0.475,
                    "assumption_rationale": ["rB"],
                },
                "modeling_notes": ["nB"],
            },
            {
                "scenario_key": "C",
                "title": "C",
                "goal": "gC",
                "target": "tC",
                "objective": "oC",
                "variables": [{"name": "x", "type": "categorical"}],
                "constraints": ["cC"],
                "tradeoff_pressure": ["tC"],
                "resistance_assumptions": {
                    "structural_conflict": 0.4,
                    "resource_reallocation_drag": 0.4,
                    "cultural_misalignment": 0.5,
                    "veto_node_intensity": 0.3,
                    "aggregate_resistance": 0.4,
                    "assumption_rationale": ["rC"],
                },
                "modeling_notes": ["nC"],
            },
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_reason_chain_contract_step_ids_and_blocking_links(tmp_path: Path, monkeypatch) -> None:
    scenario_path = tmp_path / "scenario_pack.json"
    output_path = tmp_path / "deterministic_result.json"
    _write_ontology(scenario_path)
    monkeypatch.setattr("omen.ingest.synthesizer.clients.invoke_text_prompt", _mock_reason_chain_llm)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "simulate",
            "--scenario",
            str(scenario_path),
            "--output",
            str(output_path),
        ],
    )

    main()

    reason_chain_path = scenario_path.parent / "traces" / "reason_chain.json"
    artifact = json.loads(reason_chain_path.read_text(encoding="utf-8"))
    validate_reason_chain_artifact_or_raise(artifact)

    assert artifact.get("artifact_type") == "reason_chain"
    chains = list(artifact.get("scenario_chains") or [])
    assert len(chains) == 3

    for row in chains:
        chain = row.get("reason_chain") or {}
        steps = list(chain.get("steps") or [])
        assert steps
        assert all(str(item.get("step_id") or "").strip() for item in steps)

        conclusions = chain.get("conclusions") or {}
        blocking_items = list(conclusions.get("blocking") or [])
        for blocking in blocking_items:
            assert blocking_has_activation_links(blocking)
