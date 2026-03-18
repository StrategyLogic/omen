"""Streamlit UI for Spec 6 case replay MVP (US1 baseline flow)."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from omen.ingest.llm_ontology.service import generate_strategy_ontology_from_document
from omen.scenario.case_replay_loader import save_strategy_ontology, validate_strategy_ontology
from omen.simulation.case_replay import run_case_replay_baseline
from omen.ui.artifacts import ensure_case_output_dir
from omen.ui.baseline_graph import build_baseline_path_figure
from omen.ui.generation_panel import render_generation_status


st.set_page_config(page_title="Omen Case Retro", layout="wide")
st.title("Omen · Case Retro")
st.caption("Document -> Strategy Ontology -> Baseline Simulation")

with st.sidebar:
    st.header("Inputs")
    document_path = st.text_input("Case document path", value="solution/case-xd.md")
    case_id = st.text_input("Case ID", value="x-developer-replay")
    title = st.text_input("Case Title", value="X-Developer Startup Replay")
    known_outcome = st.text_input("Known Outcome", value="project failed in market expansion")
    config_path = st.text_input("LLM Config", value="config/llm.toml")

col_gen, col_run = st.columns(2)

if "spec6_generation_result" not in st.session_state:
    st.session_state.spec6_generation_result = None
if "spec6_baseline_payload" not in st.session_state:
    st.session_state.spec6_baseline_payload = None


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
        except Exception as exc:  # pragma: no cover - UI surfaced exception
            st.error(f"Generation failed: {exc}")

with col_run:
    if st.button("Run Baseline", use_container_width=True):
        ontology_path, resolve_error = _resolve_ontology_for_baseline(case_id)
        if resolve_error or ontology_path is None:
            st.warning(resolve_error or "Ontology path resolution failed.")
        else:
            try:
                baseline = run_case_replay_baseline(
                    case_id=case_id,
                    ontology_path=ontology_path,
                )
                st.session_state.spec6_baseline_payload = baseline
                st.info(f"Baseline used ontology: {ontology_path}")
            except Exception as exc:  # pragma: no cover - UI surfaced exception
                st.error(f"Baseline run failed: {exc}")

st.divider()

if st.session_state.spec6_generation_result:
    st.subheader("Ontology Generation")
    render_generation_status(st.session_state.spec6_generation_result)
    with st.expander("Generated Strategy Ontology JSON", expanded=False):
        st.json(st.session_state.spec6_generation_result.get("strategy_ontology", {}))

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
