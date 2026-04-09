from omen.analysis.actor.insight import _extract_json_object


def test_extract_json_object_from_fenced_response() -> None:
    raw = """```json
    {"run_id":"r1","scenario_key":"A","reason_chain":{"steps":[],"intermediate":{},"conclusions":{}}}
    ```"""
    payload = _extract_json_object(raw)
    assert payload["run_id"] == "r1"
    assert payload["scenario_key"] == "A"


def test_extract_json_object_with_comments_and_trailing_commas() -> None:
    raw = """
    // model preface
    {
      "run_id": "r2",
      "scenario_key": "B",
      "reason_chain": {
        "steps": [
          {"step_id": "seed_step", "step_type": "seed", "input_refs": [], "summary": "seed",},
        ],
        "intermediate": {
          "dimension_mapping": [],
          "value_calculation": [],
        },
        "conclusions": {
          "required": [],
          "warning": [],
          "blocking": [],
        },
      },
    }
    """
    payload = _extract_json_object(raw)
    assert payload["run_id"] == "r2"
    assert payload["reason_chain"]["steps"][0]["step_id"] == "seed_step"


def test_extract_json_object_raises_for_non_json_text() -> None:
    raw = "model failed with plain text output"
    try:
        _extract_json_object(raw)
        assert False, "expected parser to fail for non-json text"
    except ValueError:
        assert True
