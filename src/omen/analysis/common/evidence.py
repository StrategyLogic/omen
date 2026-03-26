"""Evidence helpers for founder analysis outputs."""

from __future__ import annotations

from typing import Any


def unique_evidence_refs(values: list[str] | None) -> list[str]:
    if not values:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        token = str(value).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def collect_evidence_refs(*objects: Any) -> list[str]:
    refs: list[str] = []
    for obj in objects:
        if isinstance(obj, dict):
            value = obj.get("evidence_refs")
            if isinstance(value, list):
                refs.extend(str(item) for item in value)
    return unique_evidence_refs(refs)
