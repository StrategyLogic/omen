import json
import sys
from pathlib import Path

from omen.cli.main import main


def _mock_reason_chain_llm(*, config_path: str | None = None, user_prompt: str, system_prompt: str | None = None) -> str:
  _ = (config_path, user_prompt, system_prompt)
  return json.dumps(
    {
      "reason_chain": {
        "steps": [
          {"step_id": "step_1.1", "step_type": "seed", "summary": "mock", "input_refs": ["scenario::A"]},
          {"step_id": "step_2.1", "step_type": "constraint_activation", "summary": "mock", "input_refs": ["constraint::x"]},
          {"step_id": "step_3.1", "step_type": "target_or_objective", "summary": "mock", "input_refs": ["objective::x"]},
          {"step_id": "step_4.1", "step_type": "gap", "summary": "mock", "input_refs": ["step_3.outputs"]},
          {"step_id": "step_5.1", "step_type": "required_or_warning_or_blocking", "summary": "mock", "input_refs": ["step_4.outputs"]},
        ],
        "intermediate": {"dimension_mapping": [], "value_calculation": []},
        "conclusions": {
          "strategic_freedom": {
            "required": ["mock required"],
            "warning": ["mock warning"],
            "blocking": [],
          }
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
        "variables": [{"name": "x", "type": "categorical"}],
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


def test_actor_linked_paths_trace_baseline_is_stable(tmp_path: Path, monkeypatch) -> None:
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
  scenario_results = list(payload.get("scenario_results") or [])
  assert [row.get("scenario_key") for row in scenario_results] == ["A", "B", "C"]
  assert payload.get("scenario_comparison", {}).get("order") == ["A", "B", "C"]
  assert payload.get("actor_derivation_ref")

  for row in scenario_results:
    assert row.get("actor_derivation")
    assert row.get("selected_dimensions")
    conditions = row.get("scenario_conditions") or {}
    assert isinstance(conditions.get("required"), list)
    assert isinstance(conditions.get("warning"), list)
    assert isinstance(conditions.get("blocking"), list)

  derivation_path = scenario_path.parent / "traces" / "actor_derivation.json"
  derivation_payload = json.loads(derivation_path.read_text(encoding="utf-8"))
  scenario_derivations = list(derivation_payload.get("scenario_derivations") or [])
  assert [row.get("scenario_key") for row in scenario_derivations] == ["A", "B", "C"]
