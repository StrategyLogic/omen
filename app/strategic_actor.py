"""Strategic Actor Streamlit UI for Spec 7 OSS baseline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from omen.ui.actor_graph import build_actor_graph_figure
from omen.ui.artifacts import (
    ACTOR_ONTOLOGY_FILENAME,
    STRATEGY_ONTOLOGY_FILENAME,
)
from omen.ui.case_catalog import actor_output_dir, case_display_title, normalize_case_id


def _list_actor_case_ids(cases_root: str | Path = "cases/founder") -> list[str]:
    root = Path(cases_root)
    if not root.exists():
        return []
    return sorted(p.stem for p in root.glob("*.md"))


def load_actor_artifacts(case_id: str, output_root: str | Path = "output/actors") -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    case_dir = actor_output_dir(case_id, output_root=output_root)
    actor_path = case_dir / ACTOR_ONTOLOGY_FILENAME
    strategy_path = case_dir / STRATEGY_ONTOLOGY_FILENAME
    persona_path = case_dir / "analyze_persona.json"
    status_path = case_dir / "analyze_status.json"

    actor_payload = json.loads(actor_path.read_text(encoding="utf-8"))
    strategy_payload = json.loads(strategy_path.read_text(encoding="utf-8"))
    persona_payload = None
    if persona_path.exists():
        persona_payload = json.loads(persona_path.read_text(encoding="utf-8"))

    status_payload: dict[str, Any] = {"timeline": []}
    if status_path.exists():
        status_payload = json.loads(status_path.read_text(encoding="utf-8"))

    return actor_payload, strategy_payload, persona_payload or status_payload


def extract_timeline_rows(status_payload: dict[str, Any]) -> list[dict[str, Any]]:
    timeline = status_payload.get("timeline")
    if not isinstance(timeline, list):
        return []
    normalized: list[dict[str, Any]] = []
    for row in timeline:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "id": str(row.get("id") or row.get("event_id") or ""),
                "time": str(row.get("time") or "unknown"),
                "name": str(row.get("name") or row.get("event") or "unknown"),
                "description": str(
                    row.get("description")
                    or row.get("content")
                    or row.get("summary")
                    or row.get("event_excerpt")
                    or row.get("evidence")
                    or row.get("event")
                    or row.get("name")
                    or row.get("type")
                    or ""
                ),
            }
        )
    return normalized


def render_timeline(status_payload: dict[str, Any]) -> None:
    rows = extract_timeline_rows(status_payload)
    st.subheader("Timeline")
    if not rows:
        st.info("No timeline events for current status filter.")
        return

    for row in rows:
        st.markdown(f"- {row['time']} · {row['name']}")
        if row["description"]:
            st.caption(row["description"])


def _render_persona(persona_payload: dict[str, Any] | None) -> None:
    st.subheader("Strategic Actor Persona")
    if not isinstance(persona_payload, dict):
        st.info("No persona payload found. Run `omen analyze actor persona` first.")
        return

    insight = persona_payload.get("persona_insight")
    if not isinstance(insight, dict):
        st.info("No persona insight available.")
        return

    narrative = str(insight.get("narrative") or "").strip()
    if narrative:
        st.write(narrative)

    traits = insight.get("key_traits")
    if isinstance(traits, list) and traits:
        st.markdown("**Key Traits**")
        for trait in traits:
            st.markdown(f"- {trait}")


def _render_graph(actor_payload: dict[str, Any]) -> None:
    st.subheader("Actor Graph")
    figure = build_actor_graph_figure(actor_payload)
    st.plotly_chart(figure, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Strategic Actor", layout="wide")
    st.title("Strategic Actor")
    st.caption("Spec 7 OSS baseline viewer")

    case_ids = _list_actor_case_ids()
    if not case_ids:
        st.warning("No actor-source case markdown found under cases/founder/*.md")
        return

    selected_case = st.sidebar.selectbox("Case", case_ids)
    output_root = st.sidebar.text_input("Output Root", value="output/actors")

    try:
        actor_payload, strategy_payload, third_payload = load_actor_artifacts(selected_case, output_root)
    except Exception as exc:
        st.error(f"Failed to load artifacts: {exc}")
        return

    st.header(case_display_title(normalize_case_id(selected_case)))

    left, right = st.columns([1, 1])
    with left:
        _render_persona(third_payload if isinstance(third_payload, dict) and "persona_insight" in third_payload else None)
    with right:
        _render_graph(actor_payload)

    if isinstance(third_payload, dict) and "timeline" in third_payload:
        render_timeline(third_payload)
    else:
        status_path = actor_output_dir(selected_case, output_root=output_root) / "analyze_status.json"
        if status_path.exists():
            render_timeline(json.loads(status_path.read_text(encoding="utf-8")))
        else:
            render_timeline({"timeline": []})

    with st.expander("Raw Strategy Meta"):
        st.json(strategy_payload.get("meta") if isinstance(strategy_payload, dict) else {})


if __name__ == "__main__":
    main()
