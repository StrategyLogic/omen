"""Strategic Actor graph visualization helpers."""

from __future__ import annotations

from typing import Any

from omen.ui.founder_graph import build_founder_graph_figure


def build_actor_graph_figure(payload: dict[str, Any]) -> Any:
    if "founder_graph" in payload:
        return build_founder_graph_figure(payload)

    actor_payload = dict(payload)
    if "actor_graph" in actor_payload and "founder_graph" not in actor_payload:
        actor_payload["founder_graph"] = actor_payload.get("actor_graph")
    return build_founder_graph_figure(actor_payload)
