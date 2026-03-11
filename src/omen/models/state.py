"""Core state models for ontology battle simulation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ActorRuntimeState:
    actor_id: str
    actor_type: str
    budget: float
    user_base: float
    functional_profile: dict[str, float]
    user_edge_count: int = 0


@dataclass(slots=True)
class SimulationState:
    run_id: str
    step: int
    actors: dict[str, ActorRuntimeState]
    competition_edges: set[tuple[str, str]] = field(default_factory=set)
    user_overlap: dict[tuple[str, str], float] = field(default_factory=dict)

    def sorted_edges(self) -> list[tuple[str, str]]:
        return sorted(self.competition_edges)
