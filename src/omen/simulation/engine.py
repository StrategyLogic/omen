"""Deterministic simulation engine for ontology battle MVP."""

from __future__ import annotations

import random
import uuid
from dataclasses import asdict

from omen.explain.report import build_explanation_report
from omen.scenario.validator import ScenarioConfig
from omen.simulation.state import ActorRuntimeState, SimulationState
from omen.simulation.step import (
    can_apply_action,
    default_action_for,
    estimate_user_overlap,
    update_competition_edges,
    apply_action,
)


def initialize_state(config: ScenarioConfig, run_id: str | None = None) -> SimulationState:
    rid = run_id or f"run-{uuid.uuid4().hex[:10]}"
    actors: dict[str, ActorRuntimeState] = {}
    for actor in config.actors:
        actors[actor.actor_id] = ActorRuntimeState(
            actor_id=actor.actor_id,
            actor_type=actor.actor_type,
            budget=actor.budget,
            user_base=float(actor.initial_user_base),
            functional_profile=dict(actor.functional_profile),
            user_edge_count=actor.initial_user_base,
        )
    return SimulationState(
        run_id=rid,
        scenario_id=config.scenario_id,
        case_id=None,
        step=0,
        actors=actors,
    )


def _pick_actions(state: SimulationState, overlap_threshold: float) -> dict[str, str]:
    selected: dict[str, str] = {}
    actor_ids = list(state.actors)
    for actor_id, actor in state.actors.items():
        max_overlap = 0.0
        for other_id in actor_ids:
            if other_id == actor_id:
                continue
            other = state.actors[other_id]
            max_overlap = max(max_overlap, estimate_user_overlap(actor, other))

        if max_overlap >= overlap_threshold:
            action = "attack_competitor"
        else:
            action = default_action_for(actor)

        guard = can_apply_action(actor, action)
        if guard.allowed:
            selected[actor_id] = action
        else:
            selected[actor_id] = "defend_core"
    return selected


def _advance_one_step(
    state: SimulationState,
    overlap_threshold: float,
    rng: random.Random,
    random_perturbation: float,
) -> None:
    selected_actions = _pick_actions(state, overlap_threshold=overlap_threshold)
    for actor_id, action in selected_actions.items():
        actor = state.actors[actor_id]
        if can_apply_action(actor, action).allowed:
            apply_action(actor, action, rng=rng, random_perturbation=random_perturbation)
        actor.user_edge_count = int(round(actor.user_base))
    update_competition_edges(state, overlap_threshold=overlap_threshold, selected_actions=selected_actions)
    state.step += 1


def _classify_outcome(final_state: SimulationState) -> str:
    if len(final_state.competition_edges) == 0:
        return "coexistence"
    users = sorted((a.user_edge_count for a in final_state.actors.values()), reverse=True)
    if len(users) < 2:
        return "coexistence"
    if users[0] >= int(users[1] * 1.25):
        return "replacement"
    return "convergence"


def run_simulation(
    config: ScenarioConfig,
    ontology_setup: dict | None = None,
) -> dict:
    state = initialize_state(config)
    rng = random.Random(config.seed)
    snapshots: list[dict] = []
    for _ in range(config.time_steps):
        _advance_one_step(
            state,
            overlap_threshold=config.user_overlap_threshold,
            rng=rng,
            random_perturbation=config.random_perturbation,
        )
        snapshots.append(
            {
                "step": state.step,
                "competition_edges": [list(e) for e in state.sorted_edges()],
                "user_overlap": {f"{a}:{b}": v for (a, b), v in state.user_overlap.items()},
                "actors": {aid: asdict(a) for aid, a in state.actors.items()},
            }
        )

    winner = max(state.actors.values(), key=lambda x: x.user_edge_count)
    top_drivers = [
        "functional_similarity",
        "user_overlap",
        "competition_edge_activation",
    ]
    result = {
        "run_id": state.run_id,
        "scenario_id": state.scenario_id,
        "status": "completed",
        "seed": config.seed,
        "outcome_class": _classify_outcome(state),
        "winner": {
            "actor_id": winner.actor_id,
            "user_edge_count": winner.user_edge_count,
        },
        "top_drivers": top_drivers,
        "steps": config.time_steps,
        "timeline": snapshots,
        "snapshots": snapshots,
        "final_competition_edges": [list(e) for e in state.sorted_edges()],
    }
    if ontology_setup is not None:
        result["ontology_setup"] = ontology_setup
    result["explanation"] = build_explanation_report(result)
    return result
