"""Relation naming and allow-list schema constants."""

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


def is_relation_approved(name: str) -> bool:
    return name in APPROVED_RELATIONS
