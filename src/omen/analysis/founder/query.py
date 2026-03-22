"""Founder query skeleton (local, no LLM)."""

from __future__ import annotations

from typing import Any


def snapshot_by_year(founder_ontology: dict[str, Any], year: int) -> dict[str, Any]:
    events = founder_ontology.get("events") or []
    year_text = str(year)
    filtered = [event for event in events if year_text in str(event.get("date") or event.get("time") or "")]
    return {
        "year": year,
        "events": filtered,
    }
