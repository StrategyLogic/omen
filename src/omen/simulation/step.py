"""Step-level action catalog, guards, and deterministic transition helpers."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from omen.simulation.state import ActorRuntimeState, SimulationState

ACTION_CATALOG: dict[str, dict[str, float]] = {
    "grow_semantic_layer": {"semantic_delta": 0.03, "cost": 20.0, "user_growth": 0.02},
    "defend_core": {"consistency_delta": 0.02, "cost": 15.0, "user_growth": 0.01},
    "partner_ecosystem": {
        "developer_experience_delta": 0.03,
        "cost": 18.0,
        "user_growth": 0.018,
    },
    "attack_competitor": {"aggression": 1.0, "cost": 12.0, "user_growth": 0.012},
}


@dataclass(slots=True)
class ActionGuardResult:
    allowed: bool
    reason: str | None = None


def normalize_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def is_action_known(action_name: str) -> bool:
    return action_name in ACTION_CATALOG


def can_apply_action(actor: ActorRuntimeState, action_name: str) -> ActionGuardResult:
    if action_name not in ACTION_CATALOG:
        return ActionGuardResult(False, "unknown_action")

    cost = ACTION_CATALOG[action_name].get("cost", 0.0)
    if actor.budget < cost:
        return ActionGuardResult(False, "insufficient_budget")
    return ActionGuardResult(True)


def cosine_similarity(v1: dict[str, float], v2: dict[str, float]) -> float:
    keys = set(v1) | set(v2)
    dot = sum(v1.get(k, 0.0) * v2.get(k, 0.0) for k in keys)
    n1 = math.sqrt(sum(v1.get(k, 0.0) ** 2 for k in keys))
    n2 = math.sqrt(sum(v2.get(k, 0.0) ** 2 for k in keys))
    if n1 == 0 or n2 == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (n1 * n2)))


def estimate_user_overlap(a: ActorRuntimeState, b: ActorRuntimeState) -> float:
    similarity = cosine_similarity(a.functional_profile, b.functional_profile)
    scale = min(a.user_base, b.user_base) / max(a.user_base, b.user_base, 1.0)
    return max(0.0, min(1.0, similarity * scale))


def default_action_for(actor: ActorRuntimeState) -> str:
    if actor.functional_profile.get("semantic", 0.0) < 0.6:
        return "grow_semantic_layer"
    if actor.functional_profile.get("developer_experience", 0.0) < 0.7:
        return "partner_ecosystem"
    return "defend_core"


def apply_action(
    actor: ActorRuntimeState,
    action_name: str,
    rng: random.Random | None = None,
    random_perturbation: float = 0.0,
) -> None:
    payload = ACTION_CATALOG[action_name]
    actor.budget -= payload.get("cost", 0.0)
    actor.functional_profile["semantic"] = min(
        1.0, actor.functional_profile.get("semantic", 0.0) + payload.get("semantic_delta", 0.0)
    )
    actor.functional_profile["consistency"] = min(
        1.0,
        actor.functional_profile.get("consistency", 0.0) + payload.get("consistency_delta", 0.0),
    )
    actor.functional_profile["developer_experience"] = min(
        1.0,
        actor.functional_profile.get("developer_experience", 0.0)
        + payload.get("developer_experience_delta", 0.0),
    )
    growth = payload.get("user_growth", 0.0)
    if rng is not None and random_perturbation > 0.0:
        growth = growth * (1.0 + rng.uniform(-random_perturbation, random_perturbation))
    actor.user_base = max(0.0, actor.user_base * (1.0 + growth))


def update_competition_edges(
    state: SimulationState,
    overlap_threshold: float,
    selected_actions: dict[str, str],
) -> None:
    ids = list(state.actors)
    for i, aid in enumerate(ids):
        for bid in ids[i + 1 :]:
            a = state.actors[aid]
            b = state.actors[bid]
            overlap = estimate_user_overlap(a, b)
            pair = normalize_pair(aid, bid)
            state.user_overlap[pair] = overlap
            if overlap >= overlap_threshold and (
                selected_actions.get(aid) == "attack_competitor"
                or selected_actions.get(bid) == "attack_competitor"
            ):
                state.competition_edges.add(pair)
