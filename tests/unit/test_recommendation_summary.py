from omen.simulation.reason import build_recommendation_from_condition_sets


def test_recommendation_summary_no_local_template_fallback_text() -> None:
  rows = [
    {
      "scenario_key": "A",
      "scenario_conditions": {"required": [], "warning": [], "blocking": []},
    },
    {
      "scenario_key": "B",
      "scenario_conditions": {"required": [], "warning": [], "blocking": []},
    },
  ]

  summary = build_recommendation_from_condition_sets(rows)

  assert "需补齐关键执行前提" not in summary
  assert "No required condition derived from reason_chain conclusions." in summary
