from omen.simulation.reason import blocking_has_activation_links


def test_blocking_linkage_requires_activation_and_reason_refs() -> None:
  assert blocking_has_activation_links(
    {
      "text": "Insufficient migration confidence blocks move",
      "activation_step_ids": ["step_2.1"],
      "reason_step_ids": ["step_5.1"],
    }
  )


def test_blocking_linkage_rejects_missing_ref_group() -> None:
  assert not blocking_has_activation_links(
    {
      "text": "Missing activation path",
      "activation_step_ids": [],
      "reason_step_ids": ["step_5.1"],
    }
  )
