from omen.explain.generator import normalize_action_suggestion_payload


def test_action_suggestion_payload_requires_all_text_fields() -> None:
  payload = {
    "recommendation_summary": "建议优先推进A路径。",
    "gap_summary": "当前执行牵引不足，目标是形成跨部门联动闭环，关键差距在约束激活后的执行节奏。",
    "required_actions": "先明确责任闭环与时间窗，再并行化解阻断条件并建立每周证据复盘。",
  }

  normalized = normalize_action_suggestion_payload(payload)

  assert normalized is not None
  assert normalized["recommendation_summary"] == payload["recommendation_summary"]
  assert normalized["gap_summary"] == payload["gap_summary"]
  assert normalized["required_actions"] == payload["required_actions"]


def test_action_suggestion_payload_rejects_missing_required_actions() -> None:
  payload = {
    "recommendation_summary": "建议优先推进A路径。",
    "gap_summary": "当前状态与目标状态存在执行差距。",
    "required_actions": "",
  }

  assert normalize_action_suggestion_payload(payload) is None
