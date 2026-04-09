import json
import sys
from pathlib import Path

from omen.cli.main import main
from omen.ingest.validators.scenario import validate_reason_chain_view_model_artifact_or_raise


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


def test_reason_chain_view_model_contract_in_workshop_mode(tmp_path: Path, monkeypatch) -> None:
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
            "--workshop-ui-mode",
        ],
    )

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert str(payload.get("reason_chain_view_model_ref") or "").strip()

    artifact_path = scenario_path.parent / "traces" / "reason_chain_view_model.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    validate_reason_chain_view_model_artifact_or_raise(artifact)

    assert artifact.get("artifact_type") == "reason_chain_view_model"
    assert artifact.get("version") == "reason_chain_view_model_v1"
    graph = artifact.get("graph") or {}
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    assert nodes
    assert edges
    assert any(str(node.get("node_type") or "") == "reason_step" for node in nodes)
    assert any(str(node.get("node_type") or "") == "claim" for node in nodes)
