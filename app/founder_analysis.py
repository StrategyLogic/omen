"""Streamlit UI for Spec 6 case replay MVP (US1 baseline flow)."""

from __future__ import annotations

import html
import json
import re
import textwrap
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
    resolve_existing_case_output_dir,
    suggest_known_outcome,
    suggest_strategy,
)
from omen.ui.formation_graph import build_formation_chain_figure
from omen.ui.founder_graph import build_founder_graph_figure
from omen.ui.ontology_graph import build_ontology_graph_figure

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
if "spec6_pipeline_stage" not in st.session_state:
    st.session_state.spec6_pipeline_stage = "idle"
if "spec6_pipeline_progress" not in st.session_state:
    st.session_state.spec6_pipeline_progress = 0
if "spec6_pipeline_running" not in st.session_state:
    st.session_state.spec6_pipeline_running = False
if "spec6_pipeline_autorun" not in st.session_state:
    st.session_state.spec6_pipeline_autorun = False


FOUNDER_CASES_DIR = Path("cases/founder")


def _list_founder_case_ids() -> list[str]:
    if not FOUNDER_CASES_DIR.exists():
        return []
    return sorted([path.stem for path in FOUNDER_CASES_DIR.glob("*.md")])


def _suggest_founder_document_path(case_id: str) -> str:
    candidate = FOUNDER_CASES_DIR / f"{case_id}.md"
    if candidate.exists():
        return str(candidate)
    return str(candidate)


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


def _render_case_brief_panel(*, case_id: str, title: str, known_outcome: str) -> None:
    st.divider()
    st.markdown("### Case Brief")
    outcome_text = known_outcome.strip() or "Unknown"
    st.caption(f"{outcome_text}")


def _render_pipeline_journey(stage: str, message: str, paths: dict[str, Path]) -> None:
    stage_order = ["ontology", "timeline", "insight"]
    labels = {
        "ontology": ("01", "Generate Ontologies", "Build the strategy and founder ontologies."),
        "timeline": ("02", "Evidence Base", "Resolve founder relationships and event progression."),
        "insight": ("03", "Deep Insights", "Synthesize strategy formation, persona, and reality gaps."),
    }
    outputs = {
        "ontology": [paths["ontology"], paths["founder"]],
        "timeline": [paths["analyze_status"]],
        "insight": [paths["analyze_formation"], paths["analyze_insight"]],
    }

    if stage == "done":
        current_index = len(stage_order)
    else:
        current_index = stage_order.index(stage) if stage in stage_order else -1
    cols = st.columns(3)
    for idx, key in enumerate(stage_order):
        number, title, subtitle = labels[key]
        stage_outputs = [path for path in outputs[key] if path.exists()]
        if stage_outputs:
            state = "done"
            badge = "Completed"
        elif current_index == idx:
            state = "active"
            badge = "In progress"
        else:
            state = "idle"
            badge = "Pending"
        with cols[idx]:
            st.markdown(
                textwrap.dedent(
                    f"""
                    <div class="omen-step-card omen-step-{state}">
                        <div class="omen-step-number">{number}</div>
                        <div class="omen-step-title">{title}</div>
                        <div class="omen-step-copy">{subtitle}</div>
                        <div class="omen-step-badge">{badge}</div>
                    </div>
                    """
                ).strip(),
                unsafe_allow_html=True,
            )
    return


def _update_pipeline_journey(container: Any, stage: str, message: str, paths: dict[str, Path]) -> None:
    with container.container():
        _render_pipeline_journey(stage, message, paths)

with st.sidebar:
    st.markdown("## Founder Research")
    existing_case_ids = _list_founder_case_ids()
    if not existing_case_ids:
        st.error("No founder cases found under cases/founder/*.md")
        st.stop()

    loaded_case_id = st.session_state.spec6_loaded_case_id
    selected_default_case_id = loaded_case_id if loaded_case_id in existing_case_ids else existing_case_ids[0]
    selected_case_index = existing_case_ids.index(selected_default_case_id)

    case_id = st.selectbox("Case Context", options=existing_case_ids, index=selected_case_index)

    with st.expander("Settings", expanded=False):
        document_path = st.text_input(
            "Source Document",
            value=_suggest_founder_document_path(case_id),
            key=f"spec6_document_path_{case_id}",
        )
        status_date = st.text_input("Status Snapshot Date", value="")
        config_path = st.text_input("Model Config Path", value="config/llm.toml")

active_ontology_payload = _active_ontology_payload()
strategy = _extract_strategy_name(active_ontology_payload, suggest_strategy(case_id))
known_outcome = _extract_known_outcome(active_ontology_payload, suggest_known_outcome(case_id))
title = case_display_title(case_id)

st.set_page_config(page_title="Omen Strategy Reasoning Engine", layout="wide")
st.title(f"Omen · {title}")
st.caption("Turn case-style source materials into founder intelligence: extract decision-maker signals, reconstruct strategic logic, and generate deep insight.")

with st.sidebar:
    _render_case_brief_panel(
        case_id=case_id,
        title=title,
        known_outcome=known_outcome,
    )


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


def _run_omen_pipeline(
    *,
    case_id: str,
    title: str,
    document_path: str,
    strategy: str,
    known_outcome: str,
    status_date: str,
    config_path: str,
    progress_bar: Any,
    status_box: Any,
    journey_box: Any,
) -> None:
    paths = _artifact_paths(case_id)
    st.session_state.spec6_pipeline_stage = "ontology"
    st.session_state.spec6_pipeline_progress = 0
    st.session_state.spec6_pipeline_message = "Step 1/3 · Generate Ontologies"
    _update_pipeline_journey(journey_box, st.session_state.spec6_pipeline_stage, st.session_state.spec6_pipeline_message, paths)
    progress_bar.progress(0, text="Omen ready")

    status_box.info("Step 1/3 · Generate Ontologies")
    case_dir = ensure_case_output_dir(case_id)
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
    payload["ontology_path"] = str(case_dir / "strategy_ontology.json")
    st.session_state.spec6_generation_result = payload
    st.session_state.spec6_pending_strategy_updates[case_id] = _normalize_strategy_name(strategy)

    ontology_path = save_strategy_ontology(strategy_payload, case_dir / "strategy_ontology.json")
    founder_path.write_text(json.dumps(founder_payload, ensure_ascii=False, indent=2), encoding="utf-8")
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
    st.session_state.spec6_ontology_graph_payload = strategy_payload
    st.session_state.spec6_pipeline_stage = "timeline"
    st.session_state.spec6_pipeline_progress = 34
    st.session_state.spec6_pipeline_message = "Step 2/3 · Get Timeline"
    _update_pipeline_journey(journey_box, st.session_state.spec6_pipeline_stage, st.session_state.spec6_pipeline_message, paths)
    progress_bar.progress(34, text="Step 1 complete · Ontologies ready")

    status_box.info("Step 2/3 · Get Timeline")
    parsed_date = status_date.strip() or None
    status_payload = build_status_snapshot(
        strategy_ontology=strategy_payload,
        founder_ontology=founder_payload,
        year=None,
        date=parsed_date,
    )
    paths["analyze_status"].write_text(
        json.dumps(status_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    st.session_state.spec6_status_payload = status_payload
    st.session_state.spec6_pipeline_stage = "insight"
    st.session_state.spec6_pipeline_progress = 67
    st.session_state.spec6_pipeline_message = "Step 3/3 · Generate Insights"
    _update_pipeline_journey(journey_box, st.session_state.spec6_pipeline_stage, st.session_state.spec6_pipeline_message, paths)
    progress_bar.progress(67, text="Step 2 complete · Timeline loaded")

    status_box.info("Step 3/3 · Generate Insights")
    target_event_id = _pick_formation_target_event_id(founder_payload, status_payload)
    if not target_event_id:
        raise ValueError("No event id available for formation analysis.")

    formation_payload = build_strategic_formation_chain(
        founder_ontology=founder_payload,
        target_event_id=target_event_id,
    )
    paths["analyze_formation"].write_text(
        json.dumps(formation_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    st.session_state.spec6_formation_payload = formation_payload

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
    st.session_state.spec6_pipeline_stage = "done"
    st.session_state.spec6_pipeline_progress = 100
    st.session_state.spec6_pipeline_message = "Omen complete"
    _update_pipeline_journey(journey_box, st.session_state.spec6_pipeline_stage, st.session_state.spec6_pipeline_message, paths)
    progress_bar.progress(100, text="Omen complete")
    status_box.success("Omen finished · Timeline and strategic insights are ready.")
    st.session_state.spec6_output_note = "Omen pipeline completed: ontologies, timeline, formation, and insights generated."


def _inject_app_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --omen-ink: #172033;
            --omen-muted: #5b6475;
            --omen-line: rgba(23, 32, 51, 0.10);
            --omen-panel: linear-gradient(180deg, #fbfcfe 0%, #f4f7fb 100%);
            --omen-accent: #0f766e;
            --omen-accent-soft: rgba(15, 118, 110, 0.10);
        }
        .stApp {
            background: #ffffff;
        }
        .omen-summary {
            color: var(--omen-muted);
            font-size: 0.96rem;
            line-height: 1.55;
        }
        .omen-actionbar-title {
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--omen-muted);
            margin: 0.75rem 0 0.65rem;
            font-weight: 700;
        }
        .omen-timeline {
            position: relative;
            margin-top: 0.5rem;
            padding-left: 1.1rem;
            border-left: 2px solid rgba(15, 118, 110, 0.18);
        }
        .omen-timeline-item {
            position: relative;
            margin: 0 0 1rem 0.35rem;
            padding: 0.85rem 1rem 0.9rem;
            border: 1px solid var(--omen-line);
            border-radius: 16px;
            background: rgba(255,255,255,0.86);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        }
        .omen-timeline-item::before {
            content: "";
            position: absolute;
            left: -1.2rem;
            top: 1rem;
            width: 10px;
            height: 10px;
            border-radius: 999px;
            background: var(--omen-accent);
            box-shadow: 0 0 0 4px rgba(15, 118, 110, 0.12);
        }
        .omen-time {
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--omen-accent);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.35rem;
        }
        .omen-event {
            font-size: 1rem;
            font-weight: 700;
            color: var(--omen-ink);
            margin-bottom: 0.35rem;
        }
        .omen-meta {
            color: #5b6475;
            font-size: 0.9rem;
            line-height: 1.5;
        }
        .omen-badge {
            display: inline-block;
            margin-top: 0.55rem;
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            background: var(--omen-accent-soft);
            color: var(--omen-accent);
            font-size: 0.75rem;
            font-weight: 700;
        }
        .omen-step-card {
            min-height: 170px;
            padding: 0.95rem 1rem;
            border-radius: 18px;
            border: 1px solid var(--omen-line);
            background: rgba(255,255,255,0.88);
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
            margin-bottom: 0.5rem;
        }
        .omen-step-active {
            border-color: rgba(15, 118, 110, 0.32);
            background: linear-gradient(180deg, rgba(240,253,250,0.95) 0%, rgba(255,255,255,0.98) 100%);
        }
        .omen-step-done {
            border-color: rgba(15, 118, 110, 0.18);
            background: linear-gradient(180deg, rgba(248,250,252,0.95) 0%, rgba(255,255,255,0.98) 100%);
        }
        .omen-step-number {
            font-size: 0.78rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--omen-accent);
            font-weight: 800;
            margin-bottom: 0.5rem;
        }
        .omen-step-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--omen-ink);
            margin-bottom: 0.4rem;
        }
        .omen-step-copy {
            color: var(--omen-muted);
            line-height: 1.45;
            font-size: 0.92rem;
            margin-bottom: 0.85rem;
        }
        .omen-step-badge {
            display: inline-block;
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            background: var(--omen-accent-soft);
            color: var(--omen-accent);
            font-size: 0.75rem;
            font-weight: 700;
        }
        .omen-evidence-title {
            font-size: 0.78rem;
            font-weight: 700;
            color: #1d4ed8;
            margin-bottom: 0.35rem;
            letter-spacing: 0.02em;
        }
        .omen-evidence-list {
            margin: 0;
            padding-left: 1rem;
            padding-bottom: 1rem;
            color: #1e3a8a;
            font-size: 0.75rem;
            line-height: 1.45;
        }
        .omen-evidence-list li {
            margin: 0.08rem 0;
            font-size: 0.8rem;
        }
        .omen-cta-spacer {
            height: 0.95rem;
        }
        div[data-testid="stButton"] button {
            border-radius: 14px;
            min-height: 2.8rem;
            border: 1px solid rgba(23, 32, 51, 0.12);
            box-shadow: 0 8px 16px rgba(15, 23, 42, 0.06);
        }
        div[data-testid="stButton"] button[kind="primary"] {
            background: linear-gradient(135deg, #0f766e 0%, #115e59 100%);
            border: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_timeline_cards(timeline_rows: list[dict[str, Any]]) -> None:
    if not timeline_rows:
        st.info("No timeline events for current status filter.")
        return

    items: list[str] = []
    for row in timeline_rows:
        if not isinstance(row, dict):
            continue
        time_text = html.escape(str(row.get("time") or row.get("date") or "Unknown Time"))
        name_text = html.escape(str(row.get("name") or row.get("event") or "Event"))
        evidence_text = html.escape(str(row.get("evidence") or row.get("description") or "No evidence summary."))
        strategic = bool(row.get("strategic") or row.get("is_strategy_related"))
        badge = '<div class="omen-badge">Strategic signal</div>' if strategic else ""
        items.append(
            textwrap.dedent(
                f"""
                <div class="omen-timeline-item">
                    <div class="omen-time">{time_text}</div>
                    <div class="omen-event">{name_text}</div>
                    <div class="omen-meta">{evidence_text}</div>
                    {badge}
                </div>
                """
            ).strip()
        )

    html_block = '<div class="omen-timeline">' + "".join(items) + "</div>"
    st.markdown(html_block, unsafe_allow_html=True)


def _render_gap_cards(gaps: list[dict[str, Any]], *, empty_text: str) -> None:
    if not gaps:
        st.caption(empty_text)
        return

    for start in range(0, len(gaps), 2):
        left_col, right_col = st.columns(2)
        for col, gap in zip((left_col, right_col), gaps[start : start + 2]):
            if not isinstance(gap, dict):
                continue
            assumption = str(gap.get("assumption") or "Unknown Point")
            observation = str(gap.get("observation") or "...")
            significance = str(gap.get("gap_significance") or "").strip()
            event_id = str(gap.get("event_id") or "").strip()
            phase = str(gap.get("phase") or "").strip()
            refs = gap.get("evidence_refs")

            with col:
                with st.container(border=True):
                    st.markdown(f"**{assumption}**")
                    st.caption(observation)
                    meta_parts: list[str] = []
                    if phase:
                        meta_parts.append(f"Phase: {phase}")
                    if event_id:
                        meta_parts.append(f"Event: {event_id}")
                    if meta_parts:
                        st.caption(" · ".join(meta_parts))
                    if significance:
                        st.warning(significance)
                    if isinstance(refs, list) and refs:
                        st.caption("Evidence: " + ", ".join([str(item) for item in refs[:2]]))


def _render_trait_cards(key_traits: list[dict[str, Any]]) -> None:
    if not key_traits:
        st.caption("No key traits available.")
        return
    for item in key_traits:
        if not isinstance(item, dict):
            continue
        trait = str(item.get("trait") or "Unknown trait")
        evidence_summary = str(item.get("evidence_summary") or "")
        with st.container(border=True):
            st.markdown(f"**{trait}**")
            if evidence_summary:
                st.caption(evidence_summary)


_SEGMENT_PATTERN = re.compile(r"^(?P<name>[^\[\]]+?)(?:\[(?P<selectors>[^\]]+)\])?$")


def _pick_founder_actor_payload(founder_ontology: dict[str, Any] | None) -> dict[str, Any]:
    actors = founder_ontology.get("actors") if isinstance(founder_ontology, dict) else None
    if not isinstance(actors, list):
        return {}
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        actor_type = str(actor.get("type") or actor.get("role") or "").strip().lower()
        actor_id = str(actor.get("id") or "").strip().lower()
        actor_name = str(actor.get("name") or "").strip().lower()
        if "founder" in actor_type or "founder" in actor_id or "founder" in actor_name:
            return actor
    return actors[0] if actors and isinstance(actors[0], dict) else {}


def _value_to_text(value: Any) -> str:
    if isinstance(value, list):
        parts = [_value_to_text(item) for item in value]
        parts = [part for part in parts if part]
        return ", ".join(parts)
    if isinstance(value, dict):
        for key in ("value", "text", "summary", "label", "name", "description"):
            text = str(value.get(key) or "").strip()
            if text:
                return text
        parts = [_value_to_text(item) for item in value.values()]
        parts = [part for part in parts if part]
        return ", ".join(parts)
    text = str(value or "").strip()
    return text


def _select_from_list(items: list[Any], selectors: str) -> Any:
    selected: list[Any] = []
    for token in selectors.split(","):
        pick = token.strip()
        if not pick:
            continue
        if pick.isdigit():
            index = int(pick)
            if 0 <= index < len(items):
                selected.append(items[index])
            continue

        lower_pick = pick.lower()
        matched = False
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("id", "event_id", "name"):
                candidate = str(item.get(key) or "").strip().lower()
                if candidate == lower_pick:
                    selected.append(item)
                    matched = True
                    break
            if matched:
                break

    if not selected:
        return None
    return selected if len(selected) > 1 else selected[0]


def _apply_selector(current: Any, selectors: str) -> Any:
    if isinstance(current, list):
        return _select_from_list(current, selectors)
    if isinstance(current, dict):
        token = selectors.split(",", 1)[0].strip()
        if token in current:
            return current[token]
    return None


def _resolve_ref_path(path: str, context: dict[str, Any]) -> str:
    current: Any = context
    segments = [segment.strip() for segment in path.split(".") if segment.strip()]
    if not segments:
        return path

    for segment in segments:
        match = _SEGMENT_PATTERN.match(segment)
        if not match:
            return path

        name = str(match.group("name") or "").strip()
        selectors = str(match.group("selectors") or "").strip()

        if not isinstance(current, dict) or name not in current:
            return path
        current = current[name]

        if selectors:
            selected = _apply_selector(current, selectors)
            if selected is None:
                return path
            current = selected

    resolved = _value_to_text(current)
    return resolved if resolved else path


def _build_evidence_ref_context(
    *,
    case_id: str,
    formation_payload: dict[str, Any] | None,
    strategy_ontology: dict[str, Any] | None,
) -> dict[str, Any]:
    founder_payload: dict[str, Any] = {}
    founder_path = _artifact_paths(case_id)["founder"]
    if founder_path.exists():
        try:
            payload = json.loads(founder_path.read_text(encoding="utf-8"))
            founder_payload = payload if isinstance(payload, dict) else {}
        except Exception:
            founder_payload = {}

    founder_actor = _pick_founder_actor_payload(founder_payload)
    founder_profile = founder_actor.get("profile") if isinstance(founder_actor, dict) else {}
    return {
        "founder_profile": founder_profile if isinstance(founder_profile, dict) else {},
        "formation": formation_payload or {},
        "strategy_meta": (strategy_ontology or {}).get("meta") if isinstance(strategy_ontology, dict) else {},
        "events": founder_payload.get("events") if isinstance(founder_payload, dict) else [],
        "influences": founder_payload.get("influences") if isinstance(founder_payload, dict) else [],
    }


def _format_evidence_ref(ref: Any, context: dict[str, Any] | None = None) -> str:
    if isinstance(ref, dict):
        for key in ("value", "text", "summary", "label", "evidence", "content", "ref"):
            value = str(ref.get(key) or "").strip()
            if value:
                return value
        for value in ref.values():
            text = str(value or "").strip()
            if text:
                return text
        return ""

    text = str(ref).strip()
    if context and text and ("." in text or "[" in text):
        resolved = _resolve_ref_path(text, context)
        if resolved and resolved != text:
            return resolved
    return text


_inject_app_styles()


if st.session_state.spec6_loaded_case_id != case_id:
    st.session_state.spec6_generation_result = None
    st.session_state.spec6_ontology_graph_payload = None
    st.session_state.spec6_status_payload = None
    st.session_state.spec6_formation_payload = None
    st.session_state.spec6_insight_payload = None
    st.session_state.spec6_output_note = ""
    st.session_state.spec6_ontology_scope = "all"
    st.session_state.spec6_pipeline_stage = "idle"
    st.session_state.spec6_pipeline_progress = 0
    st.session_state.spec6_pipeline_message = "Waiting to start"
    _load_existing_outputs(case_id)
    st.session_state.spec6_loaded_case_id = case_id
    st.rerun()

st.markdown("#### Omen Pipeline")
journey_placeholder = st.empty()
journey_paths = _artifact_paths(case_id)
has_existing_outputs = any(path.exists() for key, path in journey_paths.items() if key != "root")
_update_pipeline_journey(
    journey_placeholder,
    st.session_state.spec6_pipeline_stage,
    st.session_state.spec6_pipeline_message,
    journey_paths,
)
st.markdown('<div class="omen-cta-spacer"></div>', unsafe_allow_html=True)
show_runtime_status = st.session_state.spec6_pipeline_running or st.session_state.spec6_pipeline_progress > 0
if show_runtime_status:
    st.markdown("#### Omen Status")
progress_placeholder = st.empty()
status_placeholder = st.empty()
cta_label = "Analysis Again" if has_existing_outputs else "Start Omen"
start_clicked = st.button(
    cta_label,
    type="primary",
    use_container_width=True,
    disabled=st.session_state.spec6_pipeline_running,
)

if start_clicked and not st.session_state.spec6_pipeline_running:
    st.session_state.spec6_pipeline_running = True
    st.session_state.spec6_pipeline_autorun = True
    st.rerun()

if st.session_state.spec6_pipeline_running and st.session_state.spec6_pipeline_autorun:
    progress_bar = progress_placeholder.progress(0, text="Starting Omen")
    try:
        _run_omen_pipeline(
            case_id=case_id,
            title=title,
            document_path=document_path,
            strategy=strategy,
            known_outcome=known_outcome,
            status_date=status_date,
            config_path=config_path,
            progress_bar=progress_bar,
            status_box=status_placeholder,
            journey_box=journey_placeholder,
        )
    except Exception as exc:  # pragma: no cover - UI surfaced exception
        st.session_state.spec6_pipeline_progress = 100
        st.session_state.spec6_pipeline_message = f"Omen failed: {exc}"
        _update_pipeline_journey(
            journey_placeholder,
            st.session_state.spec6_pipeline_stage,
            st.session_state.spec6_pipeline_message,
            journey_paths,
        )
        progress_bar.progress(100, text="Omen stopped")
        status_placeholder.error(f"Omen failed: {exc}")
        st.session_state.spec6_output_note = f"Omen failed: {exc}"
    finally:
        st.session_state.spec6_pipeline_running = False
        st.session_state.spec6_pipeline_autorun = False
else:
    if show_runtime_status:
        progress_placeholder.progress(
            st.session_state.spec6_pipeline_progress,
            text=st.session_state.spec6_pipeline_message,
        )

with st.sidebar:
    if st.session_state.spec6_output_note:
        st.info(st.session_state.spec6_output_note)

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
    evidence_ref_context = _build_evidence_ref_context(
        case_id=case_id,
        formation_payload=formation_payload,
        strategy_ontology=st.session_state.spec6_ontology_graph_payload,
    )

    t1, t2, t3 = st.tabs(["👤 Persona Narrative", "❓ Why Chain", "⚖️ Reality Gaps"])

    with t1:
        left_col, right_col = st.columns([1.0, 1.0])

        with left_col:
            st.markdown("### Founder Persona")
            st.write(persona.get("narrative", "No narrative available."))
            score_val = persona.get("consistency_score", "n/a")
            st.write(f"##### Consistency Score: {score_val}")

        with right_col:

            key_traits = persona.get("key_traits") or []
            if isinstance(key_traits, list):
                st.markdown("### Key Traits")
                _render_trait_cards(key_traits)

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
            with st.container(border=True):
                st.markdown(f"**Why {index}: {question}**")
                st.caption(answer)
                if isinstance(refs, list) and refs:
                    ref_texts = [_format_evidence_ref(ref, evidence_ref_context) for ref in refs[:3]]
                    ref_texts = [text for text in ref_texts if text]
                    if ref_texts:
                        evidence_items = "".join([f"<li>{html.escape(text)}</li>" for text in ref_texts])
                        st.markdown(
                            textwrap.dedent(
                                f"""
                                <div class="omen-evidence-title">Evidence</div>
                                <ul class="omen-evidence-list">{evidence_items}</ul>
                                """
                            ).strip(),
                            unsafe_allow_html=True,
                        )

    with t3:
        st.markdown("### Process Reality Gaps")
        process_gap_items = process_gaps if isinstance(process_gaps, list) else []
        _render_gap_cards(process_gap_items, empty_text="No process gaps available.")

        if known_outcome:
            st.markdown("### Outcome Reality Gaps")
            st.caption(f"Known Outcome: {known_outcome}")
            outcome_gap_items = outcome_gaps if isinstance(outcome_gaps, list) else []
            _render_gap_cards(outcome_gap_items, empty_text="No outcome gaps available.")

        if isinstance(learning_loop, list) and learning_loop:
            st.markdown("### Learning Loop Signals")
            for start in range(0, len(learning_loop), 2):
                lc1, lc2 = st.columns(2)
                for col, item in zip((lc1, lc2), learning_loop[start : start + 2]):
                    if not isinstance(item, dict):
                        continue
                    signal = str(item.get("signal") or "unknown_signal")
                    adjustment = str(item.get("adjustment") or "")
                    evidence_ref = str(item.get("evidence_ref") or "")
                    with col:
                        with st.container(border=True):
                            st.markdown(f"**{signal}**")
                            if adjustment:
                                st.caption(adjustment)
                            if evidence_ref:
                                st.caption(f"Evidence: {evidence_ref}")

if st.session_state.spec6_status_payload:
    st.divider()
    st.subheader("Founder Influence Graph")
    founder_fig = build_founder_graph_figure(st.session_state.spec6_status_payload)
    st.plotly_chart(founder_fig, use_container_width=True)

if st.session_state.spec6_status_payload:
    st.divider()
    status_payload = st.session_state.spec6_status_payload
    st.subheader("Timeline")
    timeline_rows = status_payload.get("timeline") or []
    _render_timeline_cards(timeline_rows)