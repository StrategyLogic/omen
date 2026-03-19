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

STRATEGY_LIBRARY: dict[str, dict[str, str]] = {
    "new_tech_market_entry": {
        "label": "New Tech Market Entry",
        "summary": "For cases where a new product enters an existing market and must overcome incumbent habits, trust gaps, and switching friction.",
        "fit": "Use when the replay depends on adoption resistance, channel education, ecosystem leverage, and timing of market entry.",
    },
    "database_paradigm_competition": {
        "label": "Database Paradigm Competition",
        "summary": "For cases where a new data architecture challenges the incumbent database mental model and developer workflow.",
        "fit": "Use when the replay hinges on paradigm shift, compatibility pressure, migration cost, and developer belief change.",
    },
}

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
if "spec6_ontology_scope" not in st.session_state:
    st.session_state.spec6_ontology_scope = "all"


def _normalize_strategy_name(value: str | None) -> str:
    if not value:
        return "case_specific_strategy"
    normalized = "_".join(value.strip().lower().replace("-", "_").split())
    return normalized or "case_specific_strategy"


def _active_ontology_payload() -> dict[str, Any] | None:
    graph_payload = st.session_state.spec6_ontology_graph_payload
    if isinstance(graph_payload, dict):
        return graph_payload
    generation_payload = st.session_state.spec6_generation_result
    if isinstance(generation_payload, dict):
        ontology_payload = generation_payload.get("strategy_ontology")
        if isinstance(ontology_payload, dict):
            return ontology_payload
    return None


def _extract_strategy_name(ontology_payload: dict[str, Any] | None, fallback: str) -> str:
    if isinstance(ontology_payload, dict):
        meta = ontology_payload.get("meta")
        if isinstance(meta, dict):
            strategy_name = str(meta.get("strategy") or "").strip()
            if strategy_name:
                return _normalize_strategy_name(strategy_name)
    return _normalize_strategy_name(fallback)


def _strategy_profile(strategy_name: str) -> dict[str, str]:
    profile = STRATEGY_LIBRARY.get(_normalize_strategy_name(strategy_name))
    if profile:
        return profile
    normalized = _normalize_strategy_name(strategy_name)
    title_case = normalized.replace("_", " ").title()
    return {
        "label": title_case,
        "summary": "Reusable strategy family for organizing cases, space ontologies, capability patterns, and axioms.",
        "fit": "Use when this case should become a repeatable strategic template instead of a one-off replay artifact.",
    }

with st.sidebar:
    st.header("Inputs")
    document_path = st.text_input("Case document path", value="solution/case-xd.md")
    case_id = st.text_input("Case ID", value="x-developer-replay")
    strategy = st.text_input("Strategy", value="new_tech_market_entry")
    known_outcome = st.text_input("Known Outcome", value="project failed in market expansion")
    config_path = st.text_input("LLM Config", value="config/llm.toml")

active_ontology_payload = _active_ontology_payload()
active_strategy = _extract_strategy_name(active_ontology_payload, strategy)
strategy_profile = _strategy_profile(active_strategy)
title = "X-Developer Startup Case"

st.set_page_config(page_title="Omen Strategy Reasoning Engine", layout="wide")
st.title(f"Omen · {title}")
st.caption(f"This case is framed as **{strategy_profile['label']}**. {strategy_profile['summary']} {strategy_profile['fit']}")

col_gen, col_graph, col_run = st.columns(3)


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
                strategy=strategy,
                known_outcome=known_outcome,
                config_path=config_path,
            )
            payload = generation.model_dump(mode="python")
            generation.strategy_ontology.setdefault("meta", {})
            generation.strategy_ontology["meta"]["strategy"] = _normalize_strategy_name(strategy)
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
                    known_outcome=known_outcome,
                )
                st.session_state.spec6_baseline_payload = baseline
                ontology_warnings = list(baseline.get("ontology_warnings") or [])
                if ontology_warnings:
                    st.session_state.spec6_output_note = (
                        f"Baseline completed with auto-fix corrections ({len(ontology_warnings)}): "
                        + " | ".join(ontology_warnings)
                    )
                else:
                    st.session_state.spec6_output_note = (
                        f"Baseline completed with ontology: {Path(ontology_path).name}"
                    )
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

    st.markdown(
        """
        <style>
        div[data-testid="stButton"] button[kind="secondary"] {
            border-radius: 999px;
            min-width: 2.75rem;
            min-height: 2.75rem;
            padding: 0 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    ontology_fig = build_ontology_graph_figure(
        ontology_payload,
        actor_scope=st.session_state.spec6_ontology_scope,
    )
    st.plotly_chart(ontology_fig, use_container_width=True)

    space_summary = _build_space_summary(ontology_payload)
    col1, col2, col3, col4, reset_col = st.columns(5)
    with col1:
        st.caption("Tech Actors")
        if st.button(str(space_summary.get("tech_space_actor_count", 0)), key="tech_actor_scope_count"):
            st.session_state.spec6_ontology_scope = "tech"
            st.rerun()
    with col2:
        st.caption("Market Actors")
        if st.button(str(space_summary.get("market_space_actor_count", 0)), key="market_actor_scope_count"):
            st.session_state.spec6_ontology_scope = "market"
            st.rerun()
    col3.metric("Shared Actors", space_summary.get("shared_actor_count", 0))
    adoption_resistance = space_summary.get("adoption_resistance")
    col4.metric("Adoption Resistance", "n/a" if adoption_resistance is None else str(adoption_resistance))

    with reset_col:
        st.caption("Show All")
        if st.button("All", key="ontology_scope_all"):
            st.session_state.spec6_ontology_scope = "all"
            st.rerun()

    current_scope_label = {
        "all": "All nodes",
        "tech": "Tech actor reachable closure",
        "market": "Market actor reachable closure",
    }.get(st.session_state.spec6_ontology_scope, "All nodes")

st.divider()

if st.session_state.spec6_baseline_payload:
    payload = st.session_state.spec6_baseline_payload
    view_model = payload.get("view_model", {})
    explanation = payload.get("explanation", {})
    st.subheader("Baseline Replay Path")
    summary = view_model.get("baseline_summary", {})

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("Outcome", summary.get("outcome", "unknown"))
    metric_col2.metric("Phases", summary.get("phase_count", 0))
    metric_col3.metric("Nodes", summary.get("node_count", 0))

    fig = build_baseline_path_figure(view_model)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Simulated vs Real Outcome")
    outcome_col1, outcome_col2 = st.columns(2)
    outcome_col1.metric("Simulated outcome", str(summary.get("outcome", "unknown")))
    outcome_col2.metric("Known real outcome", str(known_outcome))

    reality_gaps = list(explanation.get("reality_gap_analysis") or [])
    if reality_gaps:
        st.markdown("**Reality Gap Analysis**")
        for gap in reality_gaps:
            st.warning(
                (
                    f"{gap.get('factor', 'gap')}: {gap.get('reality_observation', '')} "
                    f"| calibration: {gap.get('suggested_calibration', '')}"
                )
            )

    causal_gap_links = list(view_model.get("causal_gap_links") or [])
    if causal_gap_links:
        st.markdown("**Causal-Gap Links**")
        st.json(causal_gap_links)

    editable_controls = list(view_model.get("editable_controls") or [])
    if editable_controls:
        st.markdown("**Key Calibration Controls**")
        st.json(editable_controls)

    st.subheader("Artifact Paths")
    st.code(json.dumps(payload.get("paths", {}), ensure_ascii=False, indent=2), language="json")
