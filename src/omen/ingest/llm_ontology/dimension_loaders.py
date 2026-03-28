"""Configurable founder dimension access helpers."""

from __future__ import annotations

from typing import Any, Callable


DimensionLoader = Callable[[dict[str, Any]], Any]


def _profile_section(key: str) -> DimensionLoader:
    def _loader(profile: dict[str, Any]) -> Any:
        value = profile.get(key)
        return value if isinstance(value, dict) else {}

    return _loader


DIMENSION_LOADERS: dict[str, DimensionLoader] = {
    "mental_patterns": _profile_section("mental_patterns"),
    "strategic_style": _profile_section("strategic_style"),
    "background_facts": _profile_section("background_facts"),
}


def load_founder_dimensions(
    profile: dict[str, Any],
    *,
    names: list[str] | None = None,
) -> dict[str, Any]:
    selected_names = names or list(DIMENSION_LOADERS)
    return {
        name: DIMENSION_LOADERS.get(name, lambda _: {})(profile)
        for name in selected_names
    }
