"""Identity mapping helpers between strategy and founder ontologies."""

from __future__ import annotations

from typing import Any


def build_identity_map(actors: list[dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for actor in actors:
        shared_id = str(actor.get("shared_id") or "").strip()
        founder_id = str(actor.get("id") or "").strip()
        if shared_id and founder_id:
            mapping[shared_id] = founder_id
    return mapping
