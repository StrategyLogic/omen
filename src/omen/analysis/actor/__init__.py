"""Actor analysis capabilities."""

from __future__ import annotations

from .query import build_events_snapshot, build_status_snapshot, snapshot_by_year


def generate_persona_insight(*args, **kwargs):
    from .insight import generate_persona_insight as _generate_persona_insight

    return _generate_persona_insight(*args, **kwargs)

__all__ = [
    "build_events_snapshot",
    "build_status_snapshot",
    "generate_persona_insight",
    "snapshot_by_year",
]
