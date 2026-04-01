"""Editable control derivation for case replay UI."""

from __future__ import annotations

from typing import Any


def _numeric(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_editable_controls(result: dict[str, Any]) -> list[dict[str, Any]]:
    ontology_setup = result.get("ontology_setup") or {}
    space_summary = ontology_setup.get("space_summary") or {}

    adoption_resistance = _numeric(space_summary.get("adoption_resistance"), 0.6)
    incumbent_response_speed = _numeric(space_summary.get("incumbent_response_speed"), 0.5)
    value_perception_gap = _numeric(space_summary.get("value_perception_gap"), 0.5)

    return [
        {
            "control_id": "adoption_resistance",
            "label": "Adoption resistance",
            "control_type": "parameter",
            "current_value": round(adoption_resistance, 3),
            "allowed_range": [0.0, 1.0],
            "step": 0.05,
            "source_node_id": "step-1",
        },
        {
            "control_id": "incumbent_response_speed",
            "label": "Incumbent response speed",
            "control_type": "parameter",
            "current_value": round(incumbent_response_speed, 3),
            "allowed_range": [0.0, 1.0],
            "step": 0.05,
            "source_node_id": "step-1",
        },
        {
            "control_id": "value_perception_gap",
            "label": "Value perception gap",
            "control_type": "parameter",
            "current_value": round(value_perception_gap, 3),
            "allowed_range": [0.0, 1.0],
            "step": 0.05,
            "source_node_id": "step-1",
        },
        {
            "control_id": "user_overlap_threshold",
            "label": "User overlap threshold",
            "control_type": "parameter",
            "current_value": 0.2,
            "allowed_values": [0.1, 0.2, 0.3, 0.4, 0.5],
            "source_node_id": "step-1",
        },
    ]
