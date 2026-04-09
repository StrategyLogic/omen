import json
import sys
from pathlib import Path

from omen.cli.main import main


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
                "variables": [
                    {"name": "integration_standard_adoption_rate", "type": "categorical"}
                ],
                "constraints": ["cA"],
                "tradeoff_pressure": ["tA"],
                "resistance_assumptions": {
                    "structural_conflict": 0.8,
                    "resource_reallocation_drag": 0.7,
                    "cultural_misalignment": 0.6,
                    "veto_node_intensity": 0.7,
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


def test_simulate_emits_reason_chain_artifact(tmp_path: Path, monkeypatch) -> None:
    scenario_path = tmp_path / "scenario_pack.json"
    output_path = tmp_path / "deterministic_result.json"
    _write_ontology(scenario_path)

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
    reason_chain_ref = str(payload.get("reason_chain_ref") or "")
    assert reason_chain_ref

    reason_chain_path = scenario_path.parent / "traces" / "reason_chain.json"
    assert reason_chain_path.exists()

    artifact = json.loads(reason_chain_path.read_text(encoding="utf-8"))
    assert artifact.get("artifact_type") == "reason_chain"
    assert artifact.get("version") == "reason_chain_v1"
    assert str(artifact.get("prompt_token") or "").strip()

    chains = list(artifact.get("scenario_chains") or [])
    assert [item.get("scenario_key") for item in chains] == ["A", "B", "C"]

    first_chain = chains[0].get("reason_chain") or {}
    steps = list(first_chain.get("steps") or [])
    assert [item.get("step_type") for item in steps] == [
        "seed",
        "constraint_activation",
        "target_or_objective",
        "gap",
        "required_or_warning_or_blocking",
    ]

    intermediate = first_chain.get("intermediate") or {}
    dimension_mapping = list(intermediate.get("dimension_mapping") or [])
    assert any(item.get("variable") == "integration_standard_adoption_rate" for item in dimension_mapping)
    value_calculation = list(intermediate.get("value_calculation") or [])
    assert value_calculation


def test_compare_emits_reason_chain_and_claim_linkage(tmp_path: Path, monkeypatch) -> None:
    scenario_path = tmp_path / "scenario_pack.json"
    output_path = tmp_path / "deterministic_comparison.json"
    _write_ontology(scenario_path)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "compare",
            "--scenario",
            str(scenario_path),
            "--output",
            str(output_path),
        ],
    )

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload.get("comparison_type") == "deterministic_pack"
    assert str(payload.get("reason_chain_ref") or "").strip()

    artifact_path = scenario_path.parent / "traces" / "reason_chain.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    chains = list(artifact.get("scenario_chains") or [])
    assert len(chains) == 3
    first = dict((chains[0].get("reason_chain") or {}).get("conclusions") or {})
    for bucket in ("required", "warning", "blocking"):
        for item in list(first.get(bucket) or []):
            assert list(item.get("reason_step_ids") or [])
