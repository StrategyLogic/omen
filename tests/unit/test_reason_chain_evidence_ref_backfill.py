from omen.simulation.reason import build_linked_evidence_refs


def test_evidence_refs_backfill_reason_step_ids_from_reason_chain_steps() -> None:
  reason_chain = {
    "steps": [
      {"step_id": "step_1", "step_type": "seed"},
      {"step_id": "step_2", "step_type": "constraint_activation"},
      {"step_id": "step_5", "step_type": "required_or_warning_or_blocking"},
    ],
    "conclusions": {
      "required": [
        {"text": "Must unblock alliance dependency"}
      ],
      "warning": [
        {"text": "Risk of migration delay"}
      ],
      "blocking": [
        {"text": "Cannot proceed under veto pressure"}
      ],
    },
  }

  refs = build_linked_evidence_refs(reason_chain)
  assert refs

  required = next(item for item in refs if item.get("bucket") == "required")
  warning = next(item for item in refs if item.get("bucket") == "warning")
  blocking = next(item for item in refs if item.get("bucket") == "blocking")

  assert required.get("reason_step_ids") == ["step_5"]
  assert warning.get("reason_step_ids") == ["step_5"]
  assert blocking.get("reason_step_ids") == ["step_5"]
  assert blocking.get("activation_step_ids") == ["step_2"]
