"""Map UI controls to replay override payloads."""

from __future__ import annotations

from typing import Any


CONTROL_TO_OVERRIDE_KEY: dict[str, str] = {
    "adoption_resistance": "ontology_setup.space_summary.adoption_resistance",
    "incumbent_response_speed": "ontology_setup.space_summary.incumbent_response_speed",
    "value_perception_gap": "ontology_setup.space_summary.value_perception_gap",
    "user_overlap_threshold": "user_overlap_threshold",
}


def map_control_to_overrides(control_id: str, value: Any) -> dict[str, Any]:
    if control_id not in CONTROL_TO_OVERRIDE_KEY:
        raise ValueError(f"unsupported control_id: {control_id}")
    return {CONTROL_TO_OVERRIDE_KEY[control_id]: value}
