import json
from pathlib import Path

import pytest

from omen.ingest.synthesizer.services.situation import analyze_situation_document
from omen.scenario.validator import IncompleteDeterministicPackError, validate_situation_artifact_or_raise


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

  monkeypatch.setattr("omen.ingest.synthesizer.services.situation.invoke_text_prompt", _fake_invoke)

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