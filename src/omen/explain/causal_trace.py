"""Causal gap extraction for baseline-vs-reality analysis."""

from __future__ import annotations


def extract_reality_gaps(result: dict, comparison: dict | None = None) -> list[dict]:
    ontology_setup = result.get("ontology_setup", {})
    space_summary = ontology_setup.get("space_summary", {})
    adoption_resistance = space_summary.get("adoption_resistance")

    simulated_outcome = str(result.get("outcome_class") or "unknown")
    real_world_outcome = (
        result.get("real_world_outcome")
        or result.get("known_outcome")
        or (comparison or {}).get("real_world_outcome")
    )
    winner_actor_id = result.get("winner", {}).get("actor_id")

    gaps: list[dict] = []

    if real_world_outcome and str(real_world_outcome) != simulated_outcome:
        gaps.append(
            {
                "gap_id": "GAP-outcome-mismatch",
                "factor": "simulated_vs_real_outcome",
                "model_assumption": (
                    f"Simulation outcome '{simulated_outcome}' approximates real case trajectory."
                ),
                "reality_observation": (
                    f"Known/observed real-world outcome is '{real_world_outcome}', which diverges from simulation."
                ),
                "gap_significance": "high",
                "suggested_calibration": (
                    "Recalibrate market-friction assumptions and failure activation rules for this strategy."
                ),
            }
        )

    if isinstance(adoption_resistance, (int, float)) and adoption_resistance >= 0.7:
        gaps.append(
            {
                "gap_id": "GAP-high-adoption-resistance",
                "factor": "adoption_resistance",
                "model_assumption": (
                    "Functional and competitive advantage can still translate into market expansion."
                ),
                "reality_observation": (
                    f"Adoption resistance stays high at {adoption_resistance}, indicating persistent market friction."
                ),
                "gap_significance": "high",
                "suggested_calibration": (
                    "Introduce/strengthen failure activation thresholds tied to sustained adoption resistance."
                ),
            }
        )

    if winner_actor_id and isinstance(adoption_resistance, (int, float)) and adoption_resistance >= 0.6:
        gaps.append(
            {
                "gap_id": "GAP-pilot-to-scale",
                "factor": "pilot_success_to_scale",
                "model_assumption": (
                    f"Winner emergence of '{winner_actor_id}' at simulation level implies scalable market adoption."
                ),
                "reality_observation": (
                    "Pilot-level success may not propagate to enterprise-wide rollout under organizational inertia."
                ),
                "gap_significance": "medium",
                "suggested_calibration": (
                    "Model decision-chain friction and value-perception gap in market-space parameters."
                ),
            }
        )

    return gaps
