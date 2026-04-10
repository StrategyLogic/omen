import json
from pathlib import Path

import pytest

from omen.ingest.synthesizer.services.situation import analyze_situation_document
from omen.ingest.synthesizer.services.scenario import planning
from omen.ingest.synthesizer.services.errors import LLMJsonValidationAbort
from omen.ingest.validators.scenario import IncompleteDeterministicPackError
from omen.ingest.validators.situation import validate_situation_artifact_or_raise


def test_analyze_situation_document_injects_signal_template_and_normalizes_schema(
  tmp_path: Path,
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  situation_file = tmp_path / "carrier-pressure.md"
  situation_file.write_text("Carrier pressure and ecosystem lock-in are rising.", encoding="utf-8")

  prompts: list[str] = []
  responses = iter(
    [
      json.dumps(
        {
          "title": "Carrier pressure",
          "core_question": "How should the platform respond?",
          "current_state": "Distribution leverage is shifting outward.",
          "core_dilemma": "Speed versus control",
          "key_decision_point": "Commit to a platform response",
          "target_outcomes": ["Protect adoption"],
          "hard_constraints": ["Carrier negotiation leverage"],
          "known_unknowns": ["Partner switching intent"],
        }
      ),
      json.dumps(
        {
          "version": "0.1.0",
          "id": "carrier-pressure",
          "context": {
            "title": "Carrier pressure",
            "core_question": "How should the platform respond?",
            "current_state": "Distribution leverage is shifting outward.",
            "core_dilemma": "Speed versus control",
            "key_decision_point": "Commit to a platform response",
            "target_outcomes": ["Protect adoption"],
            "hard_constraints": ["Carrier negotiation leverage"],
            "known_unknowns": ["Partner switching intent"],
          },
          "signals": [
            {
              "name": "Carrier lock-in pressure",
              "impact_type": "dampencer",
              "mapped_targets": ["platform adoption"],
            }
          ],
          "tech_space_seed": [],
          "market_space_seed": [],
          "uncertainty_space": {"overall_confidence": 0.6},
          "source_trace": [],
        }
      ),
    ]
  )

  def _fake_invoke(**kwargs: object) -> str:
    prompts.append(str(kwargs["user_prompt"]))
    return next(responses)

  monkeypatch.setattr("omen.ingest.synthesizer.builders.situation.invoke_text_prompt", _fake_invoke)

  artifact = analyze_situation_document(
    situation_file=situation_file,
    actor_ref=None,
    pack_id="carrier_v1",
    pack_version="1.0.0",
  )

  assert "signals_template_json:" in prompts[1]
  assert '"impact_types": ["driver", "constraint", "amplifier", "dampener"]' in prompts[1]

  signal = artifact["signals"][0]
  assert signal["direction"] == "down"
  assert 0.0 <= signal["strength"] <= 1.0
  assert signal["mapped_targets"][0]["impact_type"] == "dampener"
  assert signal["mapped_targets"][0]["element_key"] == "platform adoption"
  assert signal["mapped_targets"][0]["mechanism_conditions"]
  assert signal["cascade_rules"] or signal.get("no_cascade_reason")
  assert signal["market_constraints"][0]["constraint_key"] == "Carrier negotiation leverage"
  assert 0.0 <= signal["market_constraints"][0]["binding_strength"] <= 1.0
  assert signal["mechanism_note"]


def test_analyze_situation_document_requires_llm_signals(
  tmp_path: Path,
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  situation_file = tmp_path / "carrier-pressure.md"
  situation_file.write_text("Carrier pressure and ecosystem lock-in are rising.", encoding="utf-8")

  responses = iter(
    [
      json.dumps(
        {
          "title": "Carrier pressure",
          "core_question": "How should the platform respond?",
          "current_state": "Distribution leverage is shifting outward.",
          "core_dilemma": "Speed versus control",
          "key_decision_point": "Commit to a platform response",
          "target_outcomes": ["Protect adoption"],
          "hard_constraints": ["Carrier negotiation leverage"],
          "known_unknowns": ["Partner switching intent"],
        }
      ),
      json.dumps(
        {
          "version": "0.1.0",
          "id": "carrier-pressure",
          "context": {
            "title": "Carrier pressure",
            "core_question": "How should the platform respond?",
            "current_state": "Distribution leverage is shifting outward.",
            "core_dilemma": "Speed versus control",
            "key_decision_point": "Commit to a platform response",
            "target_outcomes": ["Protect adoption"],
            "hard_constraints": ["Carrier negotiation leverage"],
            "known_unknowns": ["Partner switching intent"],
          },
          "signals": [],
          "tech_space_seed": [],
          "market_space_seed": [],
          "uncertainty_space": {"overall_confidence": 0.6},
          "source_trace": [],
        }
      ),
    ]
  )

  monkeypatch.setattr(
    "omen.ingest.synthesizer.builders.situation.invoke_text_prompt",
    lambda **kwargs: next(responses),
  )

  with pytest.raises(LLMJsonValidationAbort, match="missing or empty `signals`"):
    analyze_situation_document(
      situation_file=situation_file,
      actor_ref=None,
      pack_id="carrier_v1",
      pack_version="1.0.0",
    )


def test_validate_situation_artifact_rejects_incomplete_signal_schema() -> None:
  payload = {
    "version": "0.1.0",
    "id": "carrier-pressure",
    "context": {
      "title": "Carrier pressure",
      "core_question": "How should the platform respond?",
      "current_state": "Distribution leverage is shifting outward.",
      "core_dilemma": "Speed versus control",
      "key_decision_point": "Commit to a platform response",
      "target_outcomes": ["Protect adoption"],
      "hard_constraints": ["Carrier negotiation leverage"],
      "known_unknowns": [],
    },
    "signals": [
      {
        "id": "sig-1",
        "name": "Carrier lock-in pressure",
        "domain": "market",
        "strength": 0.8,
        "direction": "down",
        "mapped_targets": [],
        "cascade_rules": [
          {
            "trigger_condition": "Carrier support remains concentrated.",
            "next_signal_id": "sig-1",
            "expected_lag": "medium",
          }
        ],
        "market_constraints": [
          {
            "constraint_key": "Carrier negotiation leverage",
            "binding_strength": 0.9,
          }
        ],
        "mechanism_note": "Carrier control suppresses platform flexibility.",
      }
    ],
    "tech_space_seed": [],
    "market_space_seed": [],
    "uncertainty_space": {"overall_confidence": 0.5},
    "source_trace": [{"trace_id": "t1", "source_kind": "doc", "source_ref": "cases/situations/carrier-pressure.md", "claim_ref": "signals[0]", "evidence_excerpt": "Carrier leverage", "confidence": 0.7}],
  }

  with pytest.raises(IncompleteDeterministicPackError, match="mapped_targets"):
    validate_situation_artifact_or_raise(payload)


def test_decompose_scenario_from_situation_coerces_scenarios_object_map(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  response_payload = {
    "pack_id": "sap_v1",
    "pack_version": "1.0.0",
    "derived_from_situation_id": "sap_reltio_acquisition",
    "ontology_version": "1.0",
    "scenarios": {
      "A": {
        "goal": "Goal A",
        "target": "Target A",
        "objective": "Objective A",
        "variables": ["var-a"],
        "constraints": ["constraint-a"],
        "tradeoff_pressure": "tradeoff-a",
        "resistance_assumptions": "resistance-a",
        "modeling_notes": "notes-a",
      },
      "B": {
        "title": "Scenario B",
        "goal": "Goal B",
        "target": "Target B",
        "objective": "Objective B",
        "variables": ["var-b"],
        "constraints": ["constraint-b"],
        "tradeoff_pressure": "tradeoff-b",
        "resistance_assumptions": "resistance-b",
        "modeling_notes": "notes-b",
      },
      "C": {
        "title": "Scenario C",
        "goal": "Goal C",
        "target": "Target C",
        "objective": "Objective C",
        "variables": ["var-c"],
        "constraints": ["constraint-c"],
        "tradeoff_pressure": "tradeoff-c",
        "resistance_assumptions": "resistance-c",
        "modeling_notes": "notes-c",
      },
    },
  }

  monkeypatch.setattr(
    "omen.ingest.synthesizer.services.scenario.invoke_text_prompt",
    lambda **kwargs: json.dumps(response_payload),
  )

  decomposition = planning(
    situation_artifact={"id": "sap_reltio_acquisition", "source_meta": {}},
    pack_id="sap_v1",
    pack_version="1.0.0",
    planning_template={},
    planning_query={},
  )

  assert isinstance(decomposition["scenarios"], list)
  assert [item.get("scenario_key") for item in decomposition["scenarios"]] == ["A", "B", "C"]
  assert decomposition["scenarios"][0]["title"].startswith("Scenario A:")
  assert decomposition["decomposition_quality"]["validation_issues"] == []