"""Explanation report utilities."""

from __future__ import annotations

from omen.explain.rule_trace import build_rule_trace_references


def build_explanation_stub(result: dict) -> dict:
    return {
        "run_id": result.get("run_id"),
        "branch_points": [],
        "causal_chain": [
            "functional_similarity increased",
            "user_overlap crossed threshold",
            "competition edges were activated",
        ],
    }

def _first_overlap_step(snapshots: list[dict]) -> int | None:
    for snapshot in snapshots:
        overlaps = snapshot.get("user_overlap", {})
        if any(value > 0 for value in overlaps.values()):
            return snapshot.get("step")
    return None


def _first_competition_step(snapshots: list[dict]) -> int | None:
    for snapshot in snapshots:
        if snapshot.get("competition_edges"):
            return snapshot.get("step")
    return None


def _winner_emergence_step(snapshots: list[dict], winner_actor_id: str | None) -> int | None:
    if not winner_actor_id:
        return None

    for snapshot in snapshots:
        actors = snapshot.get("actors", {})
        if winner_actor_id not in actors:
            continue
        winner_edges = actors[winner_actor_id].get("user_edge_count", 0)
        others = [
            payload.get("user_edge_count", 0)
            for actor_id, payload in actors.items()
            if actor_id != winner_actor_id
        ]
        if not others or winner_edges > max(others):
            return snapshot.get("step")
    return None


def build_explanation_report(result: dict, comparison: dict | None = None) -> dict:
    snapshots = result.get("snapshots", [])
    winner_actor_id = result.get("winner", {}).get("actor_id")
    ontology_setup = result.get("ontology_setup", {})
    applied_axioms = ontology_setup.get("applied_axioms", {})

    overlap_step = _first_overlap_step(snapshots)
    competition_step = _first_competition_step(snapshots)
    winner_step = _winner_emergence_step(snapshots, winner_actor_id)

    branch_points: list[dict] = []
    if overlap_step is not None:
        branch_points.append(
            {
                "step": overlap_step,
                "type": "user_overlap",
                "description": "User-group overlap emerged between strategist agents.",
            }
        )
    if competition_step is not None:
        branch_points.append(
            {
                "step": competition_step,
                "type": "competition_activation",
                "description": "Competition edges were created after overlap-triggered strategy activation.",
            }
        )
    if winner_step is not None:
        branch_points.append(
            {
                "step": winner_step,
                "type": "winner_emergence",
                "description": f"{winner_actor_id} established a leading user-edge position.",
            }
        )

    causal_chain = [
        "functional_similarity increased among strategist agents",
        "user_overlap emerged across previously separate user groups",
        "competition strategies activated and competition edges appeared",
        "user selection and substitution shifted final winner edge counts",
    ]

    narrative_parts = [
        f"Outcome class: {result.get('outcome_class')}",
        f"Winner: {winner_actor_id}",
    ]
    if overlap_step is not None:
        narrative_parts.append(f"first user overlap at step {overlap_step}")
    if competition_step is not None:
        narrative_parts.append(f"competition activated at step {competition_step}")
    if comparison:
        conditions = comparison.get("conditions", [])
        if conditions:
            condition_descriptions = [
                str(condition.get("description", "")) for condition in conditions
            ]
            condition_descriptions = [text for text in condition_descriptions if text]
            if condition_descriptions:
                narrative_parts.append(
                    "counterfactual conditions: " + " | ".join(condition_descriptions)
                )

    explanation = {
        "run_id": result.get("run_id"),
        "branch_points": branch_points,
        "causal_chain": causal_chain,
        "applied_axioms": applied_axioms,
        "rule_trace_references": build_rule_trace_references(branch_points, applied_axioms),
        "counterfactual_conditions": comparison.get("conditions", []) if comparison else [],
        "counterfactual_deltas": comparison.get("deltas", []) if comparison else [],
        "narrative_summary": "; ".join(narrative_parts),
    }
    return explanation
