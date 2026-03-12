"""Ontology vocabulary and semantic naming constraints for case ontology inputs."""

from __future__ import annotations

APPROVED_RELATIONS: set[str] = {
    "has_capability",
    "competes_with",
    "depends_on",
    "substitutes",
    "complements",
    "constrains",
    "influences",
}

ACTOR_SUFFIX = "Actor"


def is_relation_approved(name: str) -> bool:
    return name in APPROVED_RELATIONS


def looks_like_actor_concept(name: str) -> bool:
    return name.endswith(ACTOR_SUFFIX)
