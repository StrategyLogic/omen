"""Streamlit viewer for Omen Strategic Reasoning end-to-end deterministic flow artifacts."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
import textwrap
from typing import Any

import streamlit as st

from omen.scenario.loader import discover_spec8_pack_candidates, load_spec8_flow_artifacts
from omen.ui.actor_graph import build_actor_graph_figure


st.set_page_config(page_title="Omen Strategic Reasoning", layout="wide")


def _render_json(path: str, payload: dict[str, Any] | None) -> None:
    st.caption(path)
    if payload is None:
        st.warning("Artifact not found or invalid JSON")
        return
    st.json(payload, expanded=False)


def _read_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _compact_brief_markdown(markdown_text: str) -> str:
    def _format_generated_value(raw: str) -> str:
        value = str(raw or "").strip()
        if not value:
            return ""

        candidates = [value]
        if value.endswith("Z"):
            candidates.append(f"{value[:-1]}+00:00")

        for candidate in candidates:
            try:
                parsed = datetime.datetime.fromisoformat(candidate)
                return parsed.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                continue

        return value

    def _extract_generated_line(line: str) -> str:
        marker = "**Generated:**"
        raw = line.split(marker, 1)[1].strip()
        if not raw:
            return ""
        raw_value = raw.split()[0]
        formatted = _format_generated_value(raw_value)
        return f"**Generated:** {formatted}" if formatted else ""

    lines = str(markdown_text or "").splitlines()
    compact_lines: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        prefix_len = len(line) - len(stripped)
        prefix = line[:prefix_len]

        if stripped.startswith("**ID:**") or stripped.startswith("**Version:**") or stripped.startswith("**Source:**") or stripped.startswith("**Core Topic:**"):
            continue

        if stripped.startswith("**Generated:**"):
            generated_line = _extract_generated_line(stripped)
            if generated_line:
                compact_lines.append(f"{prefix}{generated_line}")
            continue

        if stripped.startswith("# "):
            continue
        if stripped.startswith("## "):
            compact_lines.append(f"{prefix}#### {stripped[3:]}")
            continue
        compact_lines.append(line)
    return "\n".join(compact_lines)


def _build_scenario_rows(scenario_pack: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in list((scenario_pack or {}).get("scenarios") or []):
        if not isinstance(scenario, dict):
            continue
        rows.append(
            {
                "Scenario": str(scenario.get("scenario_key") or ""),
                "Title": str(scenario.get("title") or ""),
                "Goal": str(scenario.get("goal") or ""),
                "Objective": str(scenario.get("objective") or ""),
                "Constraints": len(list(scenario.get("constraints") or [])),
                "Tradeoffs": len(list(scenario.get("tradeoff_pressure") or [])),
            }
        )
    return rows


def _render_trait_cards(key_traits: Any) -> None:
    if not isinstance(key_traits, list) or not key_traits:
        st.caption("No key traits available.")
        return

    for item in key_traits:
        trait_name = ""
        evidence_summary = ""
        if isinstance(item, dict):
            trait_name = str(item.get("trait") or item.get("name") or "").strip()
            evidence_summary = str(item.get("evidence_summary") or item.get("evidence") or "").strip()
        else:
            trait_name = str(item).strip()

        if not trait_name:
            continue

        with st.container(border=True):
            st.markdown(f"**{trait_name}**")
            if evidence_summary:
                st.caption(evidence_summary)


def _render_persona_panel(persona_payload: dict[str, Any] | None) -> bool:
    if not isinstance(persona_payload, dict):
        return False

    insight = persona_payload.get("persona_insight")
    if not isinstance(insight, dict):
        return False

    left_col, right_col = st.columns([1.0, 1.0])

    with left_col:
        st.markdown("#### Background story")
        narrative = str(insight.get("narrative") or "").strip()
        st.write(narrative or "No narrative available.")

        score_raw = insight.get("consistency_score")
        score_text = ""
        try:
            if score_raw is not None:
                score = float(score_raw)
                score = max(0.0, min(1.0, score))
                score_text = f"{score:.2f}"
        except Exception:
            score_text = ""

        if score_text:
            st.write(f"**Consistency score:** {score_text}")
        else:
            st.caption("No consistency score available.")

    with right_col:
        st.markdown("#### Key Traits")
        _render_trait_cards(insight.get("key_traits"))

    return bool(str(insight.get("narrative") or "").strip() or list(insight.get("key_traits") or []))


def _render_actor_graph(status_payload: dict[str, Any] | None, actor_payload: dict[str, Any] | None) -> None:
    graph_source = status_payload if isinstance(status_payload, dict) else actor_payload
    if not isinstance(graph_source, dict):
        st.info("Strategic Actor Graph unavailable: missing actor/status artifact.")
        return

    figure = build_actor_graph_figure(graph_source)
    figure.update_layout(title="Strategic Actor Graph")
    st.plotly_chart(figure, use_container_width=True)


def _build_flow_dot(payloads: dict[str, Any]) -> str:
    situation = payloads.get("situation") or {}
    context = dict(situation.get("context") or {})
    prior_snapshot = payloads.get("prior_snapshot") or {}
    result_payload = payloads.get("result") or {}
    explanation = payloads.get("explanation") or {}
    generation_trace = payloads.get("generation_trace") or {}

    priors = {
        str(item.get("scenario_key") or ""): float(item.get("score") or 0.0)
        for item in list(prior_snapshot.get("normalized_priors") or [])
        if isinstance(item, dict)
    }
    scenario_results = {
        str(item.get("scenario_key") or ""): item
        for item in list(result_payload.get("scenario_results") or [])
        if isinstance(item, dict)
    }

    confidence: dict[str, Any] = {}
    if isinstance(generation_trace.get("confidence"), dict):
        confidence = dict(generation_trace.get("confidence") or {})
    risk_raw = confidence.get("confidence_risk")
    overall_raw = confidence.get("confidence_overall")
    if overall_raw is None:
        overall_raw = confidence.get("overall_confidence")

    confidence_transition = "-"
    try:
        if risk_raw is not None and overall_raw is not None:
            confidence_transition = f"{float(risk_raw):.2f} -> {float(overall_raw):.2f}"
    except Exception:
        confidence_transition = "-"

    selected_dimensions: list[str] = []
    for row in list(result_payload.get("scenario_results") or []):
        if not isinstance(row, dict):
            continue
        selected = row.get("selected_dimensions")
        if isinstance(selected, dict):
            for item in list(selected.get("selected_dimension_keys") or []):
                token = str(item or "").strip()
                if token and token not in selected_dimensions:
                    selected_dimensions.append(token)
        derivation = row.get("actor_derivation")
        if isinstance(derivation, dict):
            for item in list(derivation.get("selected_dimensions") or []):
                token = str(item or "").strip()
                if token and token not in selected_dimensions:
                    selected_dimensions.append(token)

    def _dimensions_label(items: list[str], *, max_items: int = 6) -> str:
        if not items:
            return "-"
        lines = [f"- {item}" for item in items[:max_items]]
        if len(items) > max_items:
            lines.append("- ...")
        return "\\n".join(lines)

    dimensions_label = _dimensions_label(selected_dimensions)

    def _auto_wrap_text(value: str, *, width: int = 26, max_lines: int = 3) -> str:
        text = " ".join(str(value or "").split())
        if not text:
            return "-"
        wrapped = textwrap.wrap(
            text,
            width=width,
            break_long_words=True,
            break_on_hyphens=True,
        )
        if len(wrapped) > max_lines:
            wrapped = wrapped[:max_lines]
            wrapped[-1] = f"{wrapped[-1]}..."
        return "\\n".join(wrapped)

    def _scenario_label(key: str) -> str:
        item = dict(scenario_results.get(key) or {})
        fit = str((item.get("capability_dilemma_fit") or {}).get("fit") or "-")
        conf = str(item.get("confidence_level") or "-")
        resistance = float((item.get("resistance") or {}).get("aggregate_resistance") or 0.0)
        prior = priors.get(key)
        prior_txt = f"{prior:.2f}" if isinstance(prior, float) else "-"
        return (
            f"Scenario {key}\\n"
            f"prior={prior_txt} | fit={fit}\\n"
            f"conf={conf} | resistance={resistance:.2f}"
        )

    title = str(context.get("title") or "Strategic Situation").replace('"', "'")
    unknown_count = len(list(context.get("known_unknowns") or []))
    rec = str(explanation.get("recommendation_summary") or "Pending explanation").replace('"', "'")
    brief_label = _auto_wrap_text(title, width=36, max_lines=3)
    rec_label = _auto_wrap_text(rec, width=36, max_lines=3)

    return f"""
digraph Spec8Flow {{
  rankdir=LR;
  bgcolor="transparent";
  node [shape=box, style="rounded,filled", color="#2A2A2A", fillcolor="#F8F9FA", fontname="Helvetica", fontsize=11];
  edge [color="#4B4F56", penwidth=1.4, arrowsize=0.8];

  source [label="Source Events\\n(cases/situations/*.md)", fillcolor="#EAF4FF"];
  brief [label="Strategic Brief\\n{brief_label}", fillcolor="#EAF4FF", fixedsize=true, width=2.5, height=0.95];
  actor [label="Situation Analysis\\nconfidence: {confidence_transition}\\nKnown Unknowns({unknown_count})", fillcolor="#EEF7EC"];
  planning [label="Scenario Planning\\nA/B/C branching", fillcolor="#FFF4E8"];
  prior [label="Action Prior Probabilities\\nSelected dimensions:\\n{dimensions_label}", fillcolor="#FFF4E8"];
  concl [label="Conclusions\\nrequired / warning / blocking", fillcolor="#F3EEFF"];
  explain [label="Explanation Insights\\n{rec_label}", fillcolor="#FFEFF2", fixedsize=true, width=2.5, height=0.95];

  scenA [label="{_scenario_label('A')}", fillcolor="#FFFDF2"];
  scenB [label="{_scenario_label('B')}", fillcolor="#FFFDF2"];
  scenC [label="{_scenario_label('C')}", fillcolor="#FFFDF2"];

  source -> brief -> actor -> planning -> prior;
  prior -> scenA;
  prior -> scenB;
  prior -> scenC;
  scenA -> concl;
  scenB -> concl;
  scenC -> concl;
  concl -> explain;
}}
"""


def _render_flow_fallback(payloads: dict[str, Any]) -> None:
    prior_snapshot = payloads.get("prior_snapshot") or {}
    priors = {
        str(item.get("scenario_key") or ""): float(item.get("score") or 0.0)
        for item in list(prior_snapshot.get("normalized_priors") or [])
        if isinstance(item, dict)
    }
    st.code(
        "\n".join(
            [
                "Source (events)",
                "  -> Strategic Brief",
                "    -> Situation Analysis",
                "      -> Scenario Planning (branch)",
                f"         -> A (prior={priors.get('A', 0.0):.2f})",
                f"         -> B (prior={priors.get('B', 0.0):.2f})",
                f"         -> C (prior={priors.get('C', 0.0):.2f})",
                "      -> Conclusions",
                "        -> Explanation",
            ]
        ),
        language="text",
    )


st.markdown(
    """
    <div style="padding: 0.2rem 0 0.4rem 0;">
        <div style="font-size: 2rem; font-weight: 700; line-height: 1.2; color: #1f2937;">
            Omen Strategic Reasoning Flow
        </div>
        <div style="margin-top: 0.4rem; font-size: 1.02rem; color: #4b5563; max-width: 980px;">
            A deterministic, auditable view of the full reasoning chain: from source signals to scenario branching,
            prior-weighted paths, conclusions, and decision-ready explanation.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Data Source")
    data_root = st.text_input("Data root", value="data/scenarios")
    output_root = st.text_input("Output root", value="output")

    candidates = discover_spec8_pack_candidates(data_root=data_root, output_root=output_root)
    selected_pack = st.selectbox("Pack ID", options=candidates or [""], index=0)
    output_pack_override = st.text_input("Output pack override (optional)", value="")

if not selected_pack:
    st.info("No candidate pack found. Generate artifacts first via analyze/scenario/simulate/explain.")
    st.stop()

bundle = load_spec8_flow_artifacts(
    pack_id=selected_pack,
    data_root=data_root,
    output_root=output_root,
    output_pack_id=output_pack_override.strip() or None,
)
paths = dict(bundle.get("paths") or {})
payloads = dict(bundle.get("payloads") or {})

st.markdown(
    """
    <div style="margin-top: 0.35rem; margin-bottom: 0.25rem;">
        <span style="font-size: 1.1rem; font-weight: 650; color: #111827;">End-to-End Flow</span>
        <span style="margin-left: 0.55rem; font-size: 0.92rem; color: #6b7280;">
            Source -> Brief -> Situation Analysis -> Planning -> Prior -> A/B/C -> Conclusions -> Explanation
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)
flow_dot = _build_flow_dot(payloads)
try:
    st.graphviz_chart(flow_dot, use_container_width=True)
except Exception:
    st.info("Graphviz rendering is unavailable in this environment. Showing text fallback.")
    _render_flow_fallback(payloads)

st.caption(
    f"Loaded data pack: {bundle.get('pack_id')} | output pack: {bundle.get('output_pack_id')}"
)

tab_source, tab_actor, tab_scenario, tab_reason, tab_explain = st.tabs(
    [
        "📝 Source & Brief",
        "👤 Strategic Actor",
        "🔀 Scenario Planning",
        "🧩 Reason Chain",
        "🗣️ Explanation",
    ]
)

with tab_source:
    situation = payloads.get("situation")
    context = dict((situation or {}).get("context") or {})
    st.subheader("Summary")
    st.write(str(context.get("title") or ""))
    st.markdown(f"**Core Question**: {str(context.get('core_question') or '')}")
    st.markdown(f"**Key Decision Point**: {str(context.get('key_decision_point') or '')}")
    st.markdown(f"**Current State**: {str(context.get('current_state') or '')}")

    unknowns = list(context.get("known_unknowns") or [])
    if unknowns:
        st.markdown("**Known Unknowns**")
        for item in unknowns:
            st.write(f"- {item}")

    situation_md = Path(paths.get("situation_md") or "")
    if situation_md.exists():
        st.subheader("Context Details")
        st.markdown(_compact_brief_markdown(situation_md.read_text(encoding="utf-8")))

with tab_actor:
    st.subheader("Strategic Persona")
    actor_profile = payloads.get("actor_profile")
    actor_status = payloads.get("actor_status")
    persona_payload = payloads.get("persona") or {}
    if actor_profile:
        profile = dict(actor_profile.get("profile") or {})
        strategic_style = dict(profile.get("strategic_style") or {})
        action_prefs = list(profile.get("action_preferences") or [])

        if strategic_style:
            st.write("Strategic style")
            st.json(strategic_style, expanded=False)
        if action_prefs:
            st.write("Action preferences")
            st.json(action_prefs, expanded=False)
    else:
        st.info("Actor profile artifact unavailable. Showing derivation from simulation output.")

    has_persona_content = _render_persona_panel(persona_payload)
    persona_path = Path(paths.get("persona") or "")
    persona_exists = persona_path.exists()
    persona_payload_loaded = isinstance(persona_payload, dict) and bool(persona_payload)

    if not has_persona_content and actor_profile:
        if persona_exists and persona_payload_loaded:
            st.warning(
                "Persona artifact exists, but insight content is empty or unusable. "
                "Run `omen analyze situation --doc <name> --force` to regenerate, "
                "or run `omen analyze actor --doc <name> persona` directly."
            )
        elif persona_exists and not persona_payload_loaded:
            st.warning("Persona artifact file exists but JSON is invalid/unreadable.")
        else:
            st.info("Persona insight artifact not found yet. Run `omen analyze situation --doc <name>` again to auto-generate it after actor enhancement.")

    st.divider()
    st.subheader("Influence Graph")
    _render_actor_graph(actor_status if isinstance(actor_status, dict) else None, actor_profile if isinstance(actor_profile, dict) else None)

with tab_scenario:
    st.subheader("Deterministic Planning")
    scenario_pack_payload = payloads.get("scenario_pack") if isinstance(payloads.get("scenario_pack"), dict) else None

    scenario_pack_path = Path(paths.get("scenario_pack") or "")
    if scenario_pack_payload is None and str(scenario_pack_path):
        scenario_pack_payload = _read_json_file(scenario_pack_path)

    scenario_rows = _build_scenario_rows(scenario_pack_payload)
    if scenario_rows:
        st.dataframe(scenario_rows, use_container_width=True, hide_index=True)
    else:
        st.warning("Scenario pack artifact missing or invalid.")

    result_payload = payloads.get("result") if isinstance(payloads.get("result"), dict) else None
    derivation_rows: list[dict[str, Any]] = []
    for row in list((result_payload or {}).get("scenario_results") or []):
        if not isinstance(row, dict):
            continue
        derivation = dict(row.get("actor_derivation") or {})
        derivation_rows.append(
            {
                "Scenario": row.get("scenario_key"),
                "Decision Style": derivation.get("decision_style"),
                "Dominant Capability": derivation.get("dominant_capability"),
                "Selected Dimensions": ", ".join(list(derivation.get("selected_dimensions") or [])),
            }
        )
    if derivation_rows:
        st.markdown("### Decision Style Derivation")
        st.dataframe(derivation_rows, use_container_width=True, hide_index=True)

with tab_reason:
    st.subheader("Reason Chain Trace")
    reason_chain = payloads.get("reason_chain") or {}
    chains = list(reason_chain.get("scenario_chains") or [])
    if not chains:
        st.warning("reason_chain.json missing under data/scenarios/<pack>/traces/.")
    else:
        selected_key = st.selectbox(
            "Scenario chain",
            options=[str(row.get("scenario_key") or "") for row in chains],
            key="reason_chain_key",
        )
        row = next((item for item in chains if str(item.get("scenario_key") or "") == selected_key), {})
        chain = dict((row or {}).get("reason_chain") or {})
        steps = [item for item in list(chain.get("steps") or []) if isinstance(item, dict)]
        if steps:
            st.dataframe(
                [
                    {
                        "Step ID": s.get("step_id"),
                        "Step Type": s.get("step_type"),
                        "Summary": s.get("summary"),
                        "Confidence": s.get("confidence"),
                    }
                    for s in steps
                ],
                use_container_width=True,
                hide_index=True,
            )
        conclusions = dict(chain.get("conclusions") or {})
        st.markdown(
            f"Required: {len(list(conclusions.get('required') or []))} | "
            f"Warning: {len(list(conclusions.get('warning') or []))} | "
            f"Blocking: {len(list(conclusions.get('blocking') or []))}"
        )

with tab_explain:
    st.subheader("Decision Closure Explanation")
    explanation = payloads.get("explanation")
    if not explanation:
        st.warning("explanation.json not found. Run `omen explain --pack-id <pack-id>` first.")
    else:
        st.markdown(f"**Recommendation**: {str(explanation.get('recommendation_summary') or '')}")
        st.markdown(f"**Gap Summary**: {str(explanation.get('gap_summary') or '')}")
        st.markdown(f"**Required Actions**: {str(explanation.get('required_actions') or '')}")
        st.markdown(f"**Decision Point Response**: {str(explanation.get('decision_point_response') or '')}")

        rows = []
        for item in list(explanation.get("known_unknowns_response") or []):
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "Unknown": item.get("unknown"),
                    "Analysis": item.get("analysis"),
                    "Recommended Action": item.get("recommended_action"),
                    "Confidence": item.get("confidence"),
                }
            )
        if rows:
            st.markdown("### Known Unknown Responses")
            st.dataframe(rows, use_container_width=True, hide_index=True)

with st.expander("Artifact payloads (raw JSON)"):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### situation.json")
        _render_json(paths.get("situation", ""), payloads.get("situation"))
        st.markdown("#### scenario_pack.json")
        _render_json(paths.get("scenario_pack", ""), payloads.get("scenario_pack"))
        st.markdown("#### prior_snapshot.json")
        _render_json(paths.get("prior_snapshot", ""), payloads.get("prior_snapshot"))
    with c2:
        st.markdown("#### reason_chain.json")
        _render_json(paths.get("reason_chain", ""), payloads.get("reason_chain"))
        st.markdown("#### result.json")
        _render_json(paths.get("result", ""), payloads.get("result"))
        st.markdown("#### explanation.json")
        _render_json(paths.get("explanation", ""), payloads.get("explanation"))
