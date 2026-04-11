import json
import sys
from pathlib import Path

from omen.cli.main import main


def _mock_reason_chain_llm(*, config_path: str | None = None, user_prompt: str, system_prompt: str | None = None) -> str:
    _ = (config_path, user_prompt, system_prompt)
    if "Required keys: recommendation_summary, gap_summary, required_actions." in user_prompt:
        return json.dumps(
            {
                "recommendation_summary": "建议优先推进A路径并围绕激活约束校准执行顺序。",
                "gap_summary": "当前状态到目标状态仍存在可执行性差距，关键在于阻断项尚未被系统化化解。",
                "required_actions": "先完成阻断条件的前置解锁，再按预警强度组织验证任务并持续补证据链。",
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
                    {"step_id": "step_5.1", "step_type": "required_or_warning_or_blocking", "summary": "mock", "input_refs": ["scenario_conditions::required"]},
                ],
                "intermediate": {"dimension_mapping": [], "value_calculation": []},
                "conclusions": {"required": [], "warning": [], "blocking": []},
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


def test_reason_chain_evidence_refs_link_to_reason_steps(tmp_path: Path, monkeypatch) -> None:
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

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    rows = list(payload.get("scenario_results") or [])
    assert rows
    for row in rows:
        evidence_refs = list(row.get("evidence_refs") or [])
        assert not evidence_refs
        assert str(row.get("confidence_level") or "") == "reduced-confidence"
        missing = list((row.get("derivation_trace") or {}).get("missing_evidence_reasons") or [])
        assert missing
