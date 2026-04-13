"""Streamlit viewer for Omen Strategic Reasoning end-to-end deterministic flow artifacts."""

from __future__ import annotations

import datetime
import html
import json
import os
from pathlib import Path
import re
import textwrap
from typing import Any

import streamlit as st
import yaml

from omen.scenario.loader import discover_spec8_pack_candidates, load_spec8_flow_artifacts
from omen.ui.actor_graph import build_actor_graph_figure


st.set_page_config(page_title="Omen Strategic Reasoning", layout="wide")
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEMO_ROOT = WORKSPACE_ROOT / "demo"
DEMO_DATA_ROOT = DEMO_ROOT / "data" / "scenarios"
DEMO_OUTPUT_ROOT = DEMO_ROOT / "output"
DEMO_ACTOR_ROOT = DEMO_ROOT / "data" / "actors"


def _normalize_pack_id(value: Any) -> str:
    raw = Path(str(value or "")).stem.strip()
    return re.sub(r"[^A-Za-z0-9_.-]", "", raw)


def _render_json(path: str, payload: dict[str, Any] | None) -> None:
    st.caption(path)
    if payload is None:
        st.warning("Artifact not found or invalid JSON")
        return
    st.json(payload, expanded=False)


def _read_json_file(*, base_dir: Path, pack_id: str, filename: str) -> dict[str, Any] | None:
    try:
        workspace_base = os.path.normpath(str(WORKSPACE_ROOT.resolve()))
        base_path_obj = base_dir if base_dir.is_absolute() else (WORKSPACE_ROOT / base_dir)
        base_path = os.path.normpath(str(base_path_obj.resolve()))
        if os.path.commonpath([workspace_base, base_path]) != workspace_base:
            return None

        safe_pack_id = _normalize_pack_id(pack_id)
        if not safe_pack_id:
            return None

        fullpath = os.path.normpath(os.path.join(base_path, safe_pack_id, filename))
        if os.path.commonpath([base_path, fullpath]) != base_path:
            return None

        resolved_path = Path(fullpath)
        if not resolved_path.exists() or not resolved_path.is_file():
            return None

        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _load_sample_actor_payloads(pack_id: str) -> dict[str, Any]:
    safe_pack_id = _normalize_pack_id(pack_id)
    actor_dir = DEMO_ACTOR_ROOT / safe_pack_id
    actor_base = DEMO_ACTOR_ROOT
    actor_profile_path = actor_dir / "actor_ontology.json"
    persona_path = actor_dir / "analyze_persona.json"
    status_path = actor_dir / "analyze_status.json"

    return {
        "paths": {
            "actor_profile": str(actor_profile_path),
            "persona": str(persona_path),
            "actor_status": str(status_path),
        },
        "payloads": {
            "actor_profile": _read_json_file(base_dir=actor_base, pack_id=safe_pack_id, filename="actor_ontology.json"),
            "persona": _read_json_file(base_dir=actor_base, pack_id=safe_pack_id, filename="analyze_persona.json"),
            "actor_status": _read_json_file(base_dir=actor_base, pack_id=safe_pack_id, filename="analyze_status.json"),
        },
    }


def _load_scenario_slot_labels() -> dict[str, str]:
    file_path = Path(__file__).resolve()
    candidate_paths = [
        file_path.parents[1] / "config" / "templates" / "planning.yaml",
        file_path.parents[2] / "config" / "templates" / "planning.yaml",
    ]

    template_path = next((path for path in candidate_paths if path.exists()), None)
    if template_path is None:
        return {}

    try:
        payload = yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

    labels: dict[str, str] = {}
    for row in list(payload.get("slot_policy") or []):
        if not isinstance(row, dict):
            continue
        key = str(row.get("scenario_key") or "").strip()
        label = str(row.get("label") or "").strip()
        if key and label:
            labels[key] = label
    return labels


def _scenario_display_key(scenario_key: Any, slot_labels: dict[str, str]) -> str:
    key = str(scenario_key or "").strip()
    if not key:
        return ""
    label = str(slot_labels.get(key) or "").strip()
    return f"{key} - {label}" if label else key


def _table_cell(value: Any, *, wrap: bool = False, align: str | None = None) -> dict[str, Any]:
    return {"value": value, "wrap": bool(wrap), "align": align}


def _render_wrapped_dataframe(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    columns = list(rows[0].keys())

    def _decode_cell(value: Any) -> tuple[Any, bool, str]:
        if isinstance(value, dict) and "value" in value:
            raw_value = value.get("value")
            wrap = bool(value.get("wrap", False))
            align = str(value.get("align") or "").strip().lower()
            if align not in {"left", "right", "center"}:
                align = "right" if isinstance(raw_value, (int, float)) else "left"
            return raw_value, wrap, align
        auto_align = "right" if isinstance(value, (int, float)) else "left"
        return value, False, auto_align

    def _cell_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.3f}".rstrip("0").rstrip(".")
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    header_html = "".join(f"<th>{html.escape(str(col))}</th>" for col in columns)
    body_rows: list[str] = []
    for row in rows:
        cell_html: list[str] = []
        for col in columns:
            raw_value, should_wrap, align = _decode_cell(row.get(col))
            cell_text = html.escape(_cell_text(raw_value))
            cell_class = "wrap" if should_wrap else "nowrap"
            cell_html.append(f"<td class=\"{cell_class} align-{align}\">{cell_text}</td>")
        cells = "".join(cell_html)
        body_rows.append(f"<tr>{cells}</tr>")
    body_html = "".join(body_rows)

    st.markdown(
        f"""
        <style>
        .omen-wrap-table {{
            width: 100%;
            overflow-x: auto;
        }}
        .omen-wrap-table table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
        }}
        .omen-wrap-table th, .omen-wrap-table td {{
            border: 1px solid #E5E7EB;
            padding: 8px 10px;
            vertical-align: top;
            text-align: left;
            line-height: 1.35;
        }}
        .omen-wrap-table th {{
            background: #F9FAFB;
            word-break: normal;
            white-space: nowrap;
            font-weight: 600;
        }}
        .omen-wrap-table td.nowrap {{
            white-space: nowrap;
            word-break: normal;
            overflow-wrap: normal;
        }}
        .omen-wrap-table td.wrap {{
            white-space: normal;
            word-break: break-word;
            overflow-wrap: anywhere;
            line-height: 1.35;
        }}
        .omen-wrap-table td.align-left {{
            text-align: left;
        }}
        .omen-wrap-table td.align-right {{
            text-align: right;
            font-variant-numeric: tabular-nums;
        }}
        .omen-wrap-table td.align-center {{
            text-align: center;
        }}
        </style>
        <div class="omen-wrap-table">
          <table>
            <thead><tr>{header_html}</tr></thead>
            <tbody>{body_html}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

        if stripped.startswith("**ID:**") or stripped.startswith("**Version:**") or stripped.startswith("**Core Topic:**"):
            continue

        if stripped.startswith("**Generated:**"):
            generated_line = _extract_generated_line(stripped)
            if generated_line:
                compact_lines.append(f"\n{prefix}{generated_line}")
            continue

        if stripped.startswith("# "):
            continue
        if stripped.startswith("## "):
            compact_lines.append(f"{prefix}#### {stripped[3:]}")
            continue
        compact_lines.append(line)
    return "\n".join(compact_lines)


def _build_scenario_rows(
    scenario_pack: dict[str, Any] | None,
    *,
    slot_labels: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in list((scenario_pack or {}).get("scenarios") or []):
        if not isinstance(scenario, dict):
            continue
        rows.append(
            {
                "Scenario": _scenario_display_key(scenario.get("scenario_key"), slot_labels),
                "Title": _table_cell(str(scenario.get("title") or ""), wrap=True),
                "Long-term Goal": _table_cell(str(scenario.get("goal") or ""), wrap=True),
                "Short-term Objective": _table_cell(str(scenario.get("objective") or ""), wrap=True),
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


def _primary_actor_profile(actor_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(actor_payload, dict):
        return {}

    direct_profile = actor_payload.get("profile")
    if isinstance(direct_profile, dict) and direct_profile:
        return direct_profile

    actors = actor_payload.get("actors")
    if isinstance(actors, list):
        for item in actors:
            if not isinstance(item, dict):
                continue
            actor_type = str(item.get("type") or "").strip().lower()
            profile = item.get("profile")
            if actor_type == "strategicactor" and isinstance(profile, dict):
                return profile
        for item in actors:
            if isinstance(item, dict) and isinstance(item.get("profile"), dict):
                return dict(item.get("profile") or {})

    return {}


def _count_condition_items(items: Any) -> int:
    if not isinstance(items, list):
        return 0
    count = 0
    for item in items:
        if isinstance(item, str) and item.strip():
            count += 1
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("summary") or "").strip()
            if text or item:
                count += 1
    return count


def _reason_chain_condition_counts(conclusions: dict[str, Any]) -> tuple[int, int, int]:
    source = dict(conclusions.get("strategic_freedom") or {}) if isinstance(conclusions.get("strategic_freedom"), dict) else {}

    required_items = source.get("required") if source else conclusions.get("required")
    warning_items = source.get("warning") if source else conclusions.get("warning")
    blocking_items = source.get("blocking") if source else conclusions.get("blocking")

    return (
        _count_condition_items(required_items),
        _count_condition_items(warning_items),
        _count_condition_items(blocking_items),
    )


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
    st.header("Sample Data Source")
    st.warning("Demo mode: this app reads bundled demo artifacts only.")
    DATA_ROOT = str(DEMO_DATA_ROOT)
    OUTPUT_ROOT = str(DEMO_OUTPUT_ROOT)
    st.caption(f"Data root: {DEMO_DATA_ROOT.relative_to(WORKSPACE_ROOT)}")
    st.caption(f"Output root: {DEMO_OUTPUT_ROOT.relative_to(WORKSPACE_ROOT)}")

    candidates = discover_spec8_pack_candidates(data_root=DATA_ROOT, output_root=OUTPUT_ROOT)
    selected_pack = st.selectbox("Pack ID", options=candidates or [""], index=0)

if not selected_pack:
    st.info("No candidate pack found. Generate artifacts first via analyze/scenario/simulate/explain.")
    st.stop()

safe_pack_id = _normalize_pack_id(selected_pack)

bundle = load_spec8_flow_artifacts(
    pack_id=safe_pack_id,
    data_root=DATA_ROOT,
    output_root=OUTPUT_ROOT,
    output_pack_id=None,
)
paths = dict(bundle.get("paths") or {})
payloads = dict(bundle.get("payloads") or {})
slot_labels = _load_scenario_slot_labels()

sample_actor = _load_sample_actor_payloads(safe_pack_id)
paths.update(dict(sample_actor.get("paths") or {}))
payloads.update(dict(sample_actor.get("payloads") or {}))

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

    situation_md = None
    RAW_SIT = str(paths.get("situation_md") or "").strip()
    if RAW_SIT:
        b_path = os.path.normpath(str(WORKSPACE_ROOT))
        f_path = os.path.normpath(RAW_SIT) if os.path.isabs(RAW_SIT) else os.path.normpath(os.path.join(b_path, RAW_SIT))
        if f_path.startswith(b_path):
            situation_md = Path(f_path)

    if situation_md and situation_md.exists():
        st.subheader("Context Details")
        st.markdown(_compact_brief_markdown(situation_md.read_text(encoding="utf-8")))

with tab_actor:
    st.subheader("Strategic Persona")
    actor_profile = payloads.get("actor_profile")
    actor_status = payloads.get("actor_status")
    persona_payload = payloads.get("persona") or {}
    has_persona_content = _render_persona_panel(persona_payload)
    persona_path = None
    persona_exists = False
    RAW_PER = str(paths.get("persona") or "").strip()
    if RAW_PER:
        b_path = os.path.normpath(str(WORKSPACE_ROOT))
        f_path = os.path.normpath(RAW_PER) if os.path.isabs(RAW_PER) else os.path.normpath(os.path.join(b_path, RAW_PER))
        if f_path.startswith(b_path):
            persona_path = Path(f_path)
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
        scenario_pack_payload = _read_json_file(
            base_dir=Path(DATA_ROOT),
            pack_id=safe_pack_id,
            filename="scenario_pack.json",
        )

    scenario_rows = _build_scenario_rows(scenario_pack_payload, slot_labels=slot_labels)
    if scenario_rows:
        _render_wrapped_dataframe(scenario_rows)
    else:
        st.warning("Scenario pack artifact missing or invalid.")

    result_payload = payloads.get("result") if isinstance(payloads.get("result"), dict) else None
    prior_snapshot_payload = payloads.get("prior_snapshot")
    prior_snapshot: dict[str, Any] = dict(prior_snapshot_payload or {}) if isinstance(prior_snapshot_payload, dict) else {}
    prior_rows = list(prior_snapshot.get("normalized_priors") or prior_snapshot.get("raw_prior_scores") or [])
    prior_map: dict[str, dict[str, Any]] = {
        str(item.get("scenario_key") or ""): item
        for item in prior_rows
        if isinstance(item, dict)
    }
    derivation_rows: list[dict[str, Any]] = []
    for row in list((result_payload or {}).get("scenario_results") or []):
        if not isinstance(row, dict):
            continue
        scenario_key = str(row.get("scenario_key") or "")
        prior_item = dict(prior_map.get(scenario_key) or {})
        derivation = dict(row.get("actor_derivation") or {})
        derivation_rows.append(
            {
                "Scenario": _scenario_display_key(scenario_key, slot_labels),
                "Dominant Capability": _table_cell(derivation.get("dominant_capability"), wrap=True),
                "Action Prior Probabilities": prior_item.get("score"),
                "Explain": _table_cell(prior_item.get("explain"), wrap=True),
            }
        )
    if derivation_rows:
        st.markdown("### Decision Style Derivation")
        _render_wrapped_dataframe(derivation_rows)

with tab_reason:
    st.subheader("Reason Chain Trace")
    reason_chain = payloads.get("reason_chain") or {}
    chains = list(reason_chain.get("scenario_chains") or [])
    if not chains:
        st.warning("reason_chain.json missing under data/scenarios/<pack>/traces/.")
    else:
        chain_option_keys = [str(row.get("scenario_key") or "") for row in chains]
        selected_key = st.selectbox(
            "Scenario chain",
            options=chain_option_keys,
            format_func=lambda key: _scenario_display_key(key, slot_labels),
            key="reason_chain_key",
        )
        row = next((item for item in chains if str(item.get("scenario_key") or "") == selected_key), {})
        chain = dict((row or {}).get("reason_chain") or {})
        steps = [item for item in list(chain.get("steps") or []) if isinstance(item, dict)]
        if steps:
            _render_wrapped_dataframe(
                [
                    {
                        "Step ID": s.get("step_id"),
                        "Step Type": s.get("step_type"),
                        "Summary": _table_cell(s.get("summary"), wrap=True),
                        "Confidence": s.get("confidence"),
                    }
                    for s in steps
                ]
            )
        conclusions = dict(chain.get("conclusions") or {})
        required_count, warning_count, blocking_count = _reason_chain_condition_counts(conclusions)
        st.markdown(
            f"Required: {required_count} | "
            f"Warning: {warning_count} | "
            f"Blocking: {blocking_count}"
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
                    "Unknown": _table_cell(item.get("unknown"), wrap=True),
                    "Analysis": _table_cell(item.get("analysis"), wrap=True),
                    "Recommended Action": _table_cell(item.get("recommended_action"), wrap=True),
                    "Confidence": item.get("confidence"),
                }
            )
        if rows:
            st.markdown("### Known Unknown Responses")
            _render_wrapped_dataframe(rows)

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
