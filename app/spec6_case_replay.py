"""Streamlit UI for Spec 6 case replay MVP (US1 baseline flow)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from omen.ingest.llm_ontology.service import generate_strategy_ontology_from_document
from omen.scenario.case_replay_loader import save_strategy_ontology, validate_strategy_ontology
from omen.simulation.case_replay import run_case_replay_baseline
from omen.ui.artifacts import ensure_case_output_dir
from omen.ui.baseline_graph import build_baseline_path_figure
from omen.ui.ontology_graph import build_ontology_graph_figure


st.set_page_config(page_title="Omen Case Replay", layout="wide")
st.title("Omen · Case Replay")
st.caption("Document -> Strategy Ontology -> Baseline Replay Path")

with st.sidebar:
    st.header("Inputs")
    document_path = st.text_input("Case document path", value="solution/case-xd.md")
    case_id = st.text_input("Case ID", value="x-developer-replay")
    title = st.text_input("Case Title", value="X-Developer Startup Replay")
    known_outcome = st.text_input("Known Outcome", value="project failed in market expansion")
    config_path = st.text_input("LLM Config", value="config/llm.toml")

col_gen, col_graph, col_run = st.columns(3)

if "spec6_generation_result" not in st.session_state:
    st.session_state.spec6_generation_result = None
if "spec6_baseline_payload" not in st.session_state:
    st.session_state.spec6_baseline_payload = None
if "spec6_ontology_graph_payload" not in st.session_state:
    st.session_state.spec6_ontology_graph_payload = None
if "spec6_loaded_case_id" not in st.session_state:
    st.session_state.spec6_loaded_case_id = None
if "spec6_output_note" not in st.session_state:
    st.session_state.spec6_output_note = ""


def _artifact_paths(case_id: str) -> dict[str, Path]:
    case_dir = ensure_case_output_dir(case_id)
    return {
        "root": case_dir,
        "ontology": case_dir / "strategy_ontology.json",
        "baseline_result": case_dir / "baseline_result.json",
        "baseline_explanation": case_dir / "baseline_explanation.json",
        "view_model": case_dir / "view_model.json",
    }


def _resolve_ontology_for_baseline(case_id: str) -> tuple[str | None, str | None]:
    generation_payload = st.session_state.spec6_generation_result
    if generation_payload and generation_payload.get("validation_passed"):
        ontology_path = generation_payload.get("ontology_path")
        if ontology_path and Path(ontology_path).exists():
            return str(ontology_path), None

    case_dir = ensure_case_output_dir(case_id)
    ontology_path = case_dir / "strategy_ontology.json"
    if not ontology_path.exists():
        return None, f"Ontology file not found: {ontology_path}"

    try:
        payload = json.loads(ontology_path.read_text(encoding="utf-8"))
        validate_strategy_ontology(payload)
    except Exception as exc:
        return None, f"Existing ontology is invalid: {exc}"

    return str(ontology_path), None


def _load_existing_outputs(case_id: str) -> None:
    paths = _artifact_paths(case_id)

    if paths["ontology"].exists():
        try:
            ontology_payload = json.loads(paths["ontology"].read_text(encoding="utf-8"))
            if isinstance(ontology_payload, dict):
                st.session_state.spec6_ontology_graph_payload = ontology_payload
                st.session_state.spec6_generation_result = {
                    "ontology_path": str(paths["ontology"]),
                    "strategy_ontology": ontology_payload,
                    "validation_passed": True,
                    "validation_issues": [],
                    "reused_existing": True,
                }
        except Exception:
            st.session_state.spec6_ontology_graph_payload = None

    if paths["baseline_result"].exists() and paths["baseline_explanation"].exists() and paths["view_model"].exists():
        try:
            result_payload = json.loads(paths["baseline_result"].read_text(encoding="utf-8"))
            explanation_payload = json.loads(paths["baseline_explanation"].read_text(encoding="utf-8"))
            view_model_payload = json.loads(paths["view_model"].read_text(encoding="utf-8"))
            st.session_state.spec6_baseline_payload = {
                "result": result_payload,
                "explanation": explanation_payload,
                "view_model": view_model_payload,
                "paths": {
                    "result": str(paths["baseline_result"]),
                    "explanation": str(paths["baseline_explanation"]),
                    "view_model": str(paths["view_model"]),
                },
            }
        except Exception:
            st.session_state.spec6_baseline_payload = None


def _extract_actor_ids(actor_items: Any) -> set[str]:
    if not isinstance(actor_items, list):
        return set()

    actor_ids: set[str] = set()
    for item in actor_items:
        if isinstance(item, str):
            value = item.strip()
            if value:
                actor_ids.add(value)
            continue
        if isinstance(item, dict):
            actor_id = str(item.get("actor_id") or item.get("id") or item.get("name") or "").strip()
            if actor_id:
                actor_ids.add(actor_id)
    return actor_ids


def _extract_adoption_resistance(market_space: Any) -> Any:
    if not isinstance(market_space, dict):
        return None

    market_attributes = market_space.get("market_attributes")
    if isinstance(market_attributes, dict) and "adoption_resistance" in market_attributes:
        return market_attributes.get("adoption_resistance")

    for key in ("attributes", "properties"):
        value = market_space.get(key)
        if isinstance(value, dict) and "adoption_resistance" in value:
            return value.get("adoption_resistance")

    constraints = market_space.get("constraints")
    if isinstance(constraints, list):
        for item in constraints:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("id") or "").strip().lower()
            if "adoption_resistance" in name:
                return item.get("value")

    return None


def _build_space_summary(ontology_payload: dict[str, Any]) -> dict[str, Any]:
    tech_space = ontology_payload.get("tech_space_ontology")
    market_space = ontology_payload.get("market_space_ontology")
    shared_actor_values = ontology_payload.get("shared_actors")

    tech_actor_ids = _extract_actor_ids(tech_space.get("actors") if isinstance(tech_space, dict) else None)
    market_actor_ids = _extract_actor_ids(
        market_space.get("actors") if isinstance(market_space, dict) else None
    )
    shared_actor_ids = _extract_actor_ids(shared_actor_values)

    return {
        "tech_space_actor_count": len(tech_actor_ids),
        "market_space_actor_count": len(market_actor_ids),
        "shared_actor_count": len(shared_actor_ids),
        "adoption_resistance": _extract_adoption_resistance(market_space),
    }


def _resolve_ontology_for_graph(case_id: str) -> tuple[dict[str, Any] | None, str | None]:
    generation_payload = st.session_state.spec6_generation_result
    if generation_payload and generation_payload.get("strategy_ontology"):
        payload = generation_payload.get("strategy_ontology")
        if isinstance(payload, dict):
            return payload, None

    case_dir = ensure_case_output_dir(case_id)
    ontology_path = case_dir / "strategy_ontology.json"
    if not ontology_path.exists():
        return None, f"Ontology file not found: {ontology_path}"

    try:
        payload = json.loads(ontology_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None, "Ontology JSON root must be an object"
        return payload, None
    except Exception as exc:
        return None, f"Failed to load ontology: {exc}"


if st.session_state.spec6_loaded_case_id != case_id:
    st.session_state.spec6_generation_result = None
    st.session_state.spec6_baseline_payload = None
    st.session_state.spec6_ontology_graph_payload = None
    _load_existing_outputs(case_id)
    st.session_state.spec6_loaded_case_id = case_id

with col_gen:
    if st.button("Generate Ontology", type="primary", use_container_width=True):
        try:
            generation = generate_strategy_ontology_from_document(
                document_path=document_path,
                case_id=case_id,
                title=title,
                known_outcome=known_outcome,
                config_path=config_path,
            )
            payload = generation.model_dump(mode="python")
            st.session_state.spec6_generation_result = payload

            case_dir = ensure_case_output_dir(case_id)
            ontology_path = save_strategy_ontology(
                generation.strategy_ontology,
                case_dir / "strategy_ontology.json",
            )
            payload["ontology_path"] = str(ontology_path)
            st.session_state.spec6_generation_result = payload
            st.session_state.spec6_ontology_graph_payload = generation.strategy_ontology
            st.session_state.spec6_output_note = "Ontology generated and saved."
        except Exception as exc:  # pragma: no cover - UI surfaced exception
            st.session_state.spec6_output_note = f"Generate failed: {exc}"

with col_graph:
    if st.button("Show Ontology Graph", use_container_width=True):
        ontology_payload, resolve_error = _resolve_ontology_for_graph(case_id)
        if resolve_error or ontology_payload is None:
            st.session_state.spec6_output_note = resolve_error or "Ontology graph input is unavailable."
        else:
            st.session_state.spec6_ontology_graph_payload = ontology_payload
            st.session_state.spec6_output_note = "Ontology graph loaded."

with col_run:
    if st.button("Run Baseline", use_container_width=True):
        ontology_path, resolve_error = _resolve_ontology_for_baseline(case_id)
        if resolve_error or ontology_path is None:
            st.session_state.spec6_output_note = resolve_error or "Ontology path resolution failed."
        else:
            try:
                baseline = run_case_replay_baseline(
                    case_id=case_id,
                    ontology_path=ontology_path,
                )
                st.session_state.spec6_baseline_payload = baseline
                st.session_state.spec6_output_note = f"Baseline completed with ontology: {Path(ontology_path).name}"
            except Exception as exc:  # pragma: no cover - UI surfaced exception
                st.session_state.spec6_output_note = f"Baseline run failed: {exc}"

with st.sidebar:
    st.divider()
    st.header("Output")
    paths = _artifact_paths(case_id)
    st.caption(f"{paths['root']}")

    for label, key in (
        ("Ontology", "ontology"),
        ("Result", "baseline_result"),
        ("Explanation", "baseline_explanation"),
        ("ViewModel", "view_model"),
    ):
        filename = paths[key].name
        exists = paths[key].exists()
        prefix = "✅" if exists else "⬜"
        st.write(f"{prefix} {filename}")

    if st.session_state.spec6_output_note:
        st.info(st.session_state.spec6_output_note)

st.divider()

if st.session_state.spec6_ontology_graph_payload:
    ontology_payload = st.session_state.spec6_ontology_graph_payload
    st.subheader("Ontology Graph")
    ontology_fig = build_ontology_graph_figure(ontology_payload)
    st.plotly_chart(ontology_fig, use_container_width=True)

    space_summary = _build_space_summary(ontology_payload)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tech Actors", space_summary.get("tech_space_actor_count", 0))
    col2.metric("Market Actors", space_summary.get("market_space_actor_count", 0))
    col3.metric("Shared Actors", space_summary.get("shared_actor_count", 0))
    adoption_resistance = space_summary.get("adoption_resistance")
    col4.metric("Adoption Resistance", "n/a" if adoption_resistance is None else str(adoption_resistance))

st.divider()

if st.session_state.spec6_baseline_payload:
    payload = st.session_state.spec6_baseline_payload
    view_model = payload.get("view_model", {})
    st.subheader("Baseline Replay")
    summary = view_model.get("baseline_summary", {})

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("Outcome", summary.get("outcome", "unknown"))
    metric_col2.metric("Phases", summary.get("phase_count", 0))
    metric_col3.metric("Nodes", summary.get("node_count", 0))

    fig = build_baseline_path_figure(view_model)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Artifact Paths")
    st.code(json.dumps(payload.get("paths", {}), ensure_ascii=False, indent=2), language="json")
