from omen.analysis.actor.derivation_trace import build_actor_derivation_artifact


def test_actor_derivation_baseline_contract_fields() -> None:
  payload = build_actor_derivation_artifact(
    run_id="det-123456",
    actor_profile_ref="actor_profile_v1",
    scenario_pack_ref="strategic_actor_nokia_v1",
    scenario_derivations=[
      {
        "scenario_key": "A",
        "actor_derivation": {"decision_style": "offense_breakthrough"},
        "selected_dimensions": {"selected_dimension_keys": ["ecosystem_control"]},
        "strategic_freedom_score": 0.73,
      },
      {
        "scenario_key": "B",
        "actor_derivation": {"decision_style": "defense_resilience"},
        "selected_dimensions": {"selected_dimension_keys": ["execution_velocity"]},
        "strategic_freedom_score": 0.51,
      },
      {
        "scenario_key": "C",
        "actor_derivation": {"decision_style": "confrontation_competition"},
        "selected_dimensions": {"selected_dimension_keys": ["execution_velocity"]},
        "strategic_freedom_score": 0.49,
      },
    ],
  )

  assert payload["artifact_type"] == "actor_derivation"
  assert payload["version"] == "actor_derivation_v1"
  assert payload["run_id"] == "det-123456"
  assert payload["actor_profile_ref"] == "actor_profile_v1"
  assert payload["scenario_pack_ref"] == "strategic_actor_nokia_v1"

  rows = list(payload.get("scenario_derivations") or [])
  assert [row.get("scenario_key") for row in rows] == ["A", "B", "C"]
  assert all("actor_derivation" in row for row in rows)
  assert all("selected_dimensions" in row for row in rows)
  assert all(isinstance(row.get("strategic_freedom_score"), float) for row in rows)
