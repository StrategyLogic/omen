"""Streamlit UI for Spec 6 case replay MVP (US1 baseline flow)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from omen.analysis.founder.formation import build_strategic_formation_chain
from omen.analysis.founder.insight import generate_unified_insight
from omen.analysis.founder.query import build_status_snapshot
from omen.ingest.llm_ontology.founder_service import generate_founder_and_events_from_document
from omen.ingest.llm_ontology.service import generate_strategy_ontology_from_document
from omen.ingest.llm_ontology.strategy_assembler import attach_founder_ref, attach_timeline_events
from omen.scenario.case_replay_loader import save_strategy_ontology
from omen.ui.artifacts import ensure_case_output_dir
from omen.ui.case_catalog import (
    case_display_title,
    case_output_dir,
    default_case_id,
    list_case_ids_from_cases,
    resolve_existing_case_output_dir,
    suggest_document_path,
    suggest_known_outcome,
    suggest_strategy,
)
from omen.ui.formation_graph import build_formation_chain_figure
from omen.ui.founder_graph import build_founder_graph_figure
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
if "spec6_ontology_graph_payload" not in st.session_state:
    st.session_state.spec6_ontology_graph_payload = None
if "spec6_loaded_case_id" not in st.session_state:
    st.session_state.spec6_loaded_case_id = None
if "spec6_output_note" not in st.session_state:
    st.session_state.spec6_output_note = ""
if "spec6_ontology_scope" not in st.session_state:
    st.session_state.spec6_ontology_scope = "all"
if "spec6_status_payload" not in st.session_state:
    st.session_state.spec6_status_payload = None
if "spec6_formation_payload" not in st.session_state:
    st.session_state.spec6_formation_payload = None
if "spec6_insight_payload" not in st.session_state:
    st.session_state.spec6_insight_payload = None
if "spec6_pending_known_outcome_updates" not in st.session_state:
    st.session_state.spec6_pending_known_outcome_updates = {}
if "spec6_pending_strategy_updates" not in st.session_state:
    st.session_state.spec6_pending_strategy_updates = {}


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


def _extract_known_outcome(ontology_payload: dict[str, Any] | None, fallback: str = "") -> str:
    if isinstance(ontology_payload, dict):
        meta = ontology_payload.get("meta")
        if isinstance(meta, dict):
            known_outcome = str(meta.get("known_outcome") or "").strip()
            if known_outcome:
                return known_outcome
    return fallback


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
    existing_case_ids = list_case_ids_from_cases()
    selected_default_case_id = default_case_id(
        existing_case_ids,
        st.session_state.spec6_loaded_case_id,
    )
    if not existing_case_ids and selected_default_case_id:
        existing_case_ids = [selected_default_case_id]
    selected_case_index = existing_case_ids.index(selected_default_case_id) if existing_case_ids else 0

    case_id = st.selectbox(
        "Case ID",
        options=existing_case_ids,
        index=selected_case_index,
        help="Select a case document from cases/*.md to switch context.",
    )

    document_path = st.text_input(
        "Case document path",
        value=suggest_document_path(case_id),
        key=f"spec6_document_path_{case_id}",
    )
    strategy_key = f"spec6_strategy_{case_id}"
    pending_strategy_updates = st.session_state.spec6_pending_strategy_updates
    if isinstance(pending_strategy_updates, dict):
        pending_strategy = pending_strategy_updates.pop(case_id, None)
        if pending_strategy is not None:
            st.session_state[strategy_key] = pending_strategy
    ontology_strategy = _extract_strategy_name(_active_ontology_payload(), "")
    if strategy_key not in st.session_state:
        st.session_state[strategy_key] = ontology_strategy or suggest_strategy(case_id)
    elif ontology_strategy and not str(st.session_state.get(strategy_key) or "").strip():
        st.session_state[strategy_key] = ontology_strategy
    strategy = st.text_input(
        "Strategy",
        key=strategy_key,
    )
    known_outcome_key = f"spec6_known_outcome_{case_id}"
    pending_known_outcome_updates = st.session_state.spec6_pending_known_outcome_updates
    if isinstance(pending_known_outcome_updates, dict):
        pending_known_outcome = pending_known_outcome_updates.pop(case_id, None)
        if pending_known_outcome is not None:
            st.session_state[known_outcome_key] = pending_known_outcome
    ontology_known_outcome = _extract_known_outcome(_active_ontology_payload())
    if known_outcome_key not in st.session_state:
        st.session_state[known_outcome_key] = ontology_known_outcome or suggest_known_outcome(case_id)
    elif ontology_known_outcome and str(st.session_state.get(known_outcome_key) or "").strip().lower() in {"", "unknown"}:
        st.session_state[known_outcome_key] = ontology_known_outcome
    known_outcome = st.text_input(
        "Known Outcome",
        key=known_outcome_key,
    )
    status_date = st.text_input("Analyze Status Date", value="")
    config_path = st.text_input("LLM Config", value="config/llm.toml")

active_ontology_payload = _active_ontology_payload()
active_strategy = _extract_strategy_name(active_ontology_payload, strategy)
strategy_profile = _strategy_profile(active_strategy)
title = case_display_title(case_id)

st.set_page_config(page_title="Omen Strategy Reasoning Engine", layout="wide")
st.title(f"Omen · {title}")
st.caption(f"This case is framed as **{strategy_profile['label']}**. {strategy_profile['summary']} {strategy_profile['fit']}")

col_gen, col_status, col_run, col_insight = st.columns(4)


def _artifact_paths(case_id: str) -> dict[str, Path]:
    case_dir = resolve_existing_case_output_dir(case_id)
    return {
        "root": case_dir,
        "ontology": case_dir / "strategy_ontology.json",
        "founder": case_dir / "founder_ontology.json",
        "analyze_status": case_dir / "analyze_status.json",
        "analyze_formation": case_dir / "analyze_formation.json",
        "analyze_insight": case_dir / "analyze_insight.json",
    }


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
                strategy_name = _extract_strategy_name(ontology_payload, "")
                if strategy_name:
                    st.session_state.spec6_pending_strategy_updates[case_id] = strategy_name
                known_outcome = _extract_known_outcome(ontology_payload)
                if known_outcome:
                    st.session_state.spec6_pending_known_outcome_updates[case_id] = known_outcome
        except Exception:
            st.session_state.spec6_ontology_graph_payload = None

    if paths["analyze_status"].exists():
        try:
            status_payload = json.loads(paths["analyze_status"].read_text(encoding="utf-8"))
            st.session_state.spec6_status_payload = status_payload if isinstance(status_payload, dict) else None
        except Exception:
            st.session_state.spec6_status_payload = None

    if paths["analyze_formation"].exists():
        try:
            formation_payload = json.loads(paths["analyze_formation"].read_text(encoding="utf-8"))
            st.session_state.spec6_formation_payload = formation_payload if isinstance(formation_payload, dict) else None
        except Exception:
            st.session_state.spec6_formation_payload = None
    st.session_state.spec6_insight_payload = None

    if paths["analyze_insight"].exists():
        try:
            insight_payload = json.loads(paths["analyze_insight"].read_text(encoding="utf-8"))
            st.session_state.spec6_insight_payload = insight_payload if isinstance(insight_payload, dict) else None
        except Exception:
            st.session_state.spec6_insight_payload = None


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


def _display_output_subpath(case_id: str) -> str:
    output_path = case_output_dir(case_id)
    try:
        output_root = output_path.parents[1]
        return str(output_path.relative_to(output_root))
    except Exception:
        return str(output_path)


def _pick_formation_target_event_id(founder_payload: dict[str, Any], status_payload: dict[str, Any] | None) -> str | None:
    timeline = (status_payload or {}).get("timeline") if isinstance(status_payload, dict) else None
    if isinstance(timeline, list) and timeline:
        for item in reversed(timeline):
            if isinstance(item, dict):
                event_id = str(item.get("id") or "").strip()
                if event_id:
                    return event_id

    events = founder_payload.get("events")
    if isinstance(events, list) and events:
        for item in reversed(events):
            if isinstance(item, dict):
                event_id = str(item.get("id") or "").strip()
                if event_id:
                    return event_id
    return None


if st.session_state.spec6_loaded_case_id != case_id:
    st.session_state.spec6_generation_result = None
    st.session_state.spec6_ontology_graph_payload = None
    st.session_state.spec6_status_payload = None
    st.session_state.spec6_formation_payload = None
    st.session_state.spec6_insight_payload = None
    st.session_state.spec6_output_note = ""
    st.session_state.spec6_ontology_scope = "all"
    _load_existing_outputs(case_id)
    st.session_state.spec6_loaded_case_id = case_id
    st.rerun()

with col_gen:
    if st.button("Generate Ontology", type="primary", use_container_width=True):
        try:
            # Step 1: Ensure directory exists BEFORE running LLM
            case_dir = ensure_case_output_dir(case_id)
            st.session_state.spec6_output_note = f"Directory verified: {case_dir}"
            
            generation = generate_strategy_ontology_from_document(
                document_path=document_path,
                case_id=case_id,
                title=title,
                strategy=strategy,
                known_outcome=known_outcome,
                config_path=config_path,
            )
            known_outcome_effective = generation.inferred_known_outcome or known_outcome
            if generation.inferred_known_outcome:
                st.session_state.spec6_pending_known_outcome_updates[case_id] = generation.inferred_known_outcome

            founder_payload, timeline_events = generate_founder_and_events_from_document(
                document_path=document_path,
                case_id=case_id,
                title=title,
                known_outcome=known_outcome_effective,
                config_path=config_path,
            )

            strategy_payload = attach_timeline_events(generation.strategy_ontology, timeline_events)

            case_dir = ensure_case_output_dir(case_id)
            founder_path = case_dir / "founder_ontology.json"
            strategy_payload = attach_founder_ref(
                strategy_payload,
                founder_payload,
                founder_filename=founder_path.name,
            )

            payload = generation.model_dump(mode="python")
            strategy_payload.setdefault("meta", {})
            strategy_payload["meta"]["strategy"] = _normalize_strategy_name(strategy)
            strategy_payload["meta"]["known_outcome"] = known_outcome_effective
            payload["strategy_ontology"] = strategy_payload
            st.session_state.spec6_generation_result = payload
            st.session_state.spec6_pending_strategy_updates[case_id] = _normalize_strategy_name(strategy)

            ontology_path = save_strategy_ontology(
                strategy_payload,
                case_dir / "strategy_ontology.json",
            )
            founder_path.write_text(json.dumps(founder_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            # Generate and save generation.json to match CLI behavior
            report = {
                "case_id": case_id,
                "strategy_ontology_path": str(ontology_path),
                "founder_ontology_path": str(founder_path),
                "validation_passed": generation.validation_passed,
                "validation_issues": generation.validation_issues,
                "reused_existing": False,
            }
            (case_dir / "generation.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

            payload["ontology_path"] = str(ontology_path)
            st.session_state.spec6_generation_result = payload
            st.session_state.spec6_ontology_graph_payload = strategy_payload
            st.session_state.spec6_output_note = "Ontology + founder slice generated and saved."
            st.rerun()
        except Exception as exc:  # pragma: no cover - UI surfaced exception
            st.session_state.spec6_output_note = f"Generate failed: {exc}"

with col_status:
    if st.button("Analyze Founder", use_container_width=True):
        paths = _artifact_paths(case_id)
        if not paths["ontology"].exists() or not paths["founder"].exists():
            st.session_state.spec6_output_note = (
                "Analyze founder requires existing strategy_ontology.json and founder_ontology.json."
            )
        else:
            try:
                strategy_payload = json.loads(paths["ontology"].read_text(encoding="utf-8"))
                founder_payload = json.loads(paths["founder"].read_text(encoding="utf-8"))
                parsed_date = status_date.strip() or None
                status_payload = build_status_snapshot(
                    strategy_ontology=strategy_payload,
                    founder_ontology=founder_payload,
                    year=None,
                    date=parsed_date,
                )
                st.session_state.spec6_ontology_graph_payload = strategy_payload
                paths["analyze_status"].write_text(
                    json.dumps(status_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                st.session_state.spec6_status_payload = status_payload
                st.session_state.spec6_output_note = (
                    "Analyze status loaded from existing artifacts (strategy ontology graph included)."
                )
            except Exception as exc:  # pragma: no cover - UI surfaced exception
                st.session_state.spec6_output_note = f"Analyze status failed: {exc}"

with col_run:
    if st.button("Analyze Formation", use_container_width=True):
        paths = _artifact_paths(case_id)
        if not paths["founder"].exists():
            st.session_state.spec6_output_note = "Analyze formation requires existing founder_ontology.json."
        else:
            try:
                founder_payload = json.loads(paths["founder"].read_text(encoding="utf-8"))
                target_event_id = _pick_formation_target_event_id(
                    founder_payload,
                    st.session_state.spec6_status_payload,
                )
                if not target_event_id:
                    st.session_state.spec6_output_note = "No event id available for formation analysis."
                else:
                    formation_payload = build_strategic_formation_chain(
                        founder_ontology=founder_payload,
                        target_event_id=target_event_id,
                    )
                    paths["analyze_formation"].write_text(
                        json.dumps(formation_payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    st.session_state.spec6_formation_payload = formation_payload
                    st.session_state.spec6_output_note = f"Analyze formation generated for event: {target_event_id}"
            except Exception as exc:  # pragma: no cover - UI surfaced exception
                st.session_state.spec6_output_note = f"Analyze formation failed: {exc}"
with col_insight:
    if st.button("Deep Insight", use_container_width=True):
        paths = _artifact_paths(case_id)
        if not paths["founder"].exists() or not paths["analyze_formation"].exists():
            st.session_state.spec6_output_note = "Deep Insight requires existing founder_ontology.json and analyze_formation.json."
        else:
            try:
                founder_payload = json.loads(paths["founder"].read_text(encoding="utf-8"))
                formation_payload = json.loads(paths["analyze_formation"].read_text(encoding="utf-8"))
                strategy_payload = None
                if paths["ontology"].exists():
                    strategy_payload = json.loads(paths["ontology"].read_text(encoding="utf-8"))
                insight_payload = generate_unified_insight(
                    case_id=case_id,
                    founder_ontology=founder_payload,
                    strategy_ontology=strategy_payload,
                    formation_payload=formation_payload,
                    config_path=config_path,
                )
                paths["analyze_insight"].write_text(
                    json.dumps(insight_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                st.session_state.spec6_insight_payload = insight_payload
                st.session_state.spec6_output_note = "Deep Insight (Narrative + Gaps) generated."
            except Exception as exc:
                st.session_state.spec6_output_note = f"Deep Insight failed: {exc}"


with st.sidebar:
    st.divider()
    st.header("Output")
    paths = _artifact_paths(case_id)
    st.caption(_display_output_subpath(case_id))

    for label, key in (
        ("Ontology", "ontology"),
        ("Founder", "founder"),
        ("AnalyzeStatus", "analyze_status"),
        ("AnalyzeFormation", "analyze_formation"),
        ("AnalyzeInsight", "analyze_insight"),
    ):
        filename = paths[key].name
        exists = paths[key].exists()
        prefix = "✅" if exists else "⬜"
        st.write(f"{prefix} {filename}")

    if st.session_state.spec6_output_note:
        st.info(st.session_state.spec6_output_note)

st.divider()

if st.session_state.spec6_status_payload:
    status_payload = st.session_state.spec6_status_payload
    st.subheader("Analyze Status")

    summary = status_payload.get("summary") or {}

    timeline_rows = status_payload.get("timeline") or []
    if timeline_rows:
        st.markdown("**Timeline**")
        import pandas as pd
        df_timeline = pd.DataFrame(timeline_rows)
        # Display only requested columns in specific order
        requested_cols = ["time", "name", "evidence", "strategic"]
        available_cols = [c for c in requested_cols if c in df_timeline.columns]
        df_timeline = df_timeline[available_cols]
        st.dataframe(df_timeline, use_container_width=True)
    else:
        st.info("No timeline events for current status filter.")

st.divider()

if st.session_state.spec6_insight_payload:
    insight_payload = st.session_state.spec6_insight_payload
    st.subheader("Deep Strategic Insight")

    persona = insight_payload.get("persona_insight") or {}
    why_chain = insight_payload.get("why_chain") or []
    gap_analysis = insight_payload.get("gap_analysis") or {}
    process_gaps = gap_analysis.get("process_gaps") or []
    outcome_gaps = gap_analysis.get("outcome_gaps") or []
    learning_loop = gap_analysis.get("learning_loop") or []
    known_outcome = str(gap_analysis.get("known_outcome") or "").strip()
    formation_payload = st.session_state.spec6_formation_payload

    t1, t2, t3 = st.tabs(["👤 Persona Narrative", "❓ Why Chain", "⚖️ Reality Gaps"])

    with t1:
        st.markdown("### Founder Persona")
        st.write(persona.get("narrative", "No narrative available."))
        st.markdown(f"**Consistency Score:** {persona.get('consistency_score', 'n/a')}")

        if st.session_state.spec6_status_payload:
            founder_fig = build_founder_graph_figure(st.session_state.spec6_status_payload)
            st.plotly_chart(founder_fig, use_container_width=True)

        key_traits = persona.get("key_traits") or []
        if isinstance(key_traits, list) and key_traits:
            st.markdown("**Key Traits**")
            for item in key_traits:
                if not isinstance(item, dict):
                    continue
                trait = str(item.get("trait") or "Unknown trait")
                evidence_summary = str(item.get("evidence_summary") or "")
                st.info(f"{trait}: {evidence_summary}")

    with t2:
        if formation_payload:
            st.markdown("### Strategic Formation Chain")
            summary = formation_payload.get("summary") or {}
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            metric_col1.metric("Perception Signals", int(summary.get("perception_signal_count") or 0))
            metric_col2.metric("Internal Constraints", int(summary.get("internal_constraint_count") or 0))
            metric_col3.metric("External Pressures", int(summary.get("external_pressure_count") or 0))
            metric_col4.metric("Execution Deltas", int(summary.get("execution_delta_count") or 0))

            formation_fig = build_formation_chain_figure(formation_payload)
            st.plotly_chart(formation_fig, use_container_width=True)

        st.markdown("### Why: Strategic Formation Narrative")
        why_items = why_chain if isinstance(why_chain, list) else []
        for index, item in enumerate(why_items, start=1):
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or f"Why {index}?")
            answer = str(item.get("answer") or "No answer available.")
            refs = item.get("evidence_refs") or []
            with st.expander(f"Why {index}: {question}", expanded=index == 1):
                st.write(answer)
                if isinstance(refs, list) and refs:
                    st.caption("Evidence refs: " + ", ".join([str(ref) for ref in refs[:3]]))

        if formation_payload:
            chain = formation_payload.get("formation_chain") or {}
            with st.expander("Formation Data Details"):
                st.markdown("**Perception**")
                st.json(chain.get("perception") or [])
                st.markdown("**Constraint Conflict**")
                st.json(chain.get("constraint_conflict") or {})
                st.markdown("**Mediation (Mental Patterns / Strategic Style)**")
                st.json(chain.get("mediation") or {})
                st.markdown("**Decision Logic**")
                st.json(chain.get("decision_logic") or {})
                st.markdown("**Execution Delta**")
                st.json(chain.get("execution_delta") or [])

    with t3:
        st.markdown("### Process Reality Gaps")
        process_gap_items = process_gaps if isinstance(process_gaps, list) else []
        for gap in process_gap_items:
            with st.expander(f"Gap: {gap.get('assumption', 'Unknown Point')}"):
                st.write(f"**Observed Reality:** {gap.get('observation', '...')}")
                if gap.get('gap_significance'):
                    st.warning(f"**Significance:** {gap.get('gap_significance')}")
                event_id = str(gap.get("event_id") or "").strip()
                phase = str(gap.get("phase") or "").strip()
                if event_id:
                    st.caption(f"Event: {event_id}")
                if phase:
                    st.caption(f"Phase: {phase}")

        if known_outcome:
            st.markdown("### Outcome Reality Gaps")
            st.caption(f"Known Outcome: {known_outcome}")
            outcome_gap_items = outcome_gaps if isinstance(outcome_gaps, list) else []
            for gap in outcome_gap_items:
                with st.expander(f"Outcome Gap: {gap.get('assumption', 'Unknown Point')}"):
                    st.write(f"**Observed Outcome:** {gap.get('observation', '...')}")
                    if gap.get('gap_significance'):
                        st.warning(f"**Significance:** {gap.get('gap_significance')}")
                    event_id = str(gap.get("event_id") or "").strip()
                    phase = str(gap.get("phase") or "").strip()
                    if event_id:
                        st.caption(f"Event: {event_id}")
                    if phase:
                        st.caption(f"Phase: {phase}")

        if isinstance(learning_loop, list) and learning_loop:
            st.markdown("### Learning Loop Signals")
            for item in learning_loop:
                if not isinstance(item, dict):
                    continue
                signal = str(item.get("signal") or "unknown_signal")
                adjustment = str(item.get("adjustment") or "")
                evidence_ref = str(item.get("evidence_ref") or "")
                st.info(f"{signal}: {adjustment}")
                if evidence_ref:
                    st.caption(f"Evidence: {evidence_ref}")

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
    reset_col, col1, col2, col3, col4 = st.columns(5)
    with reset_col:
        st.caption("Show")
        if st.button("All", key="ontology_scope_all"):
            st.session_state.spec6_ontology_scope = "all"
            st.rerun()
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

    current_scope_label = {
        "all": "All nodes",
        "tech": "Tech actor reachable closure",
        "market": "Market actor reachable closure",
    }.get(st.session_state.spec6_ontology_scope, "All nodes")

