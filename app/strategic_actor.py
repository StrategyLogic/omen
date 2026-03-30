"""Strategic Actor Streamlit UI."""

from __future__ import annotations

import html
import json
import textwrap
from pathlib import Path
from typing import Any

import streamlit as st

from omen.analysis.founder.insight import generate_persona_insight
from omen.analysis.founder.query import build_events_snapshot
from omen.ingest.llm_ontology.actor_service import generate_actor_and_events_from_document
from omen.ingest.llm_ontology.service import generate_strategy_ontology_from_document
from omen.ingest.llm_ontology.strategy_assembler import attach_actor_ref, attach_timeline_events
from omen.scenario.case_replay_loader import save_strategy_ontology
from omen.ui.actor_graph import build_actor_graph_figure
from omen.ui.artifacts import ACTOR_ONTOLOGY_FILENAME, STRATEGY_ONTOLOGY_FILENAME, ensure_actor_output_dir
from omen.ui.case_catalog import actor_output_dir, case_display_title, normalize_case_id, suggest_known_outcome


if not hasattr(st, "session_state"):
    st.session_state = {}

if "spec7_ui_lang" not in st.session_state:
    st.session_state["spec7_ui_lang"] = "zh"
if "spec7_pipeline_running" not in st.session_state:
    st.session_state["spec7_pipeline_running"] = False
if "spec7_pipeline_autorun" not in st.session_state:
    st.session_state["spec7_pipeline_autorun"] = False
if "spec7_pipeline_progress" not in st.session_state:
    st.session_state["spec7_pipeline_progress"] = 0
if "spec7_output_note" not in st.session_state:
    st.session_state["spec7_output_note"] = ""


UI_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "language_selector": "Language / 语言",
        "sidebar_title": "Omen Strategic Reasoning Engine",
        "sidebar_intro": "Omen is an open-source strategic reasoning engine that helps decision-makers unravel the logic behind complex phenomena, providing not only conclusions but also replayable, explainable, and actionable strategic insights.",
        "no_cases_found": "No file found under cases/actors/*.md",
        "case_context": "Select Case",
        "settings": "Settings",
        "output_root": "Output Root",
        "page_title": "Strategic Actor Research",
        "page_intro": "With just one case document, gain insights into the core beliefs, motivations, key events, and close influence relationships of strategic actors with one click.",
        "pipeline_title": "Automated Workflow",
        "step1_title": "Build Ontology",
        "step1_copy": "Generate strategy and actor ontologies.",
        "step2_title": "Extract Facts",
        "step2_copy": "Including events, relations, and timeline.",
        "step3_title": "Deep Insights",
        "step3_copy": "Generate persona, traits, and influence graph.",
        "badge_done": "Completed",
        "badge_pending": "Pending",
        "deep_insight": "Deep Insights",
        "tab_persona": "👤 Strategic Persona",
        "actor_persona": "Background story",
        "no_persona": "No persona payload found. Run `omen analyze actor --doc <name>` first.",
        "no_narrative": "No narrative available.",
        "key_traits": "Key Traits",
        "no_traits": "No key traits available.",
        "influence_graph": "Influence Graph",
        "timeline": "Timeline",
        "no_timeline": "No timeline events for current status filter.",
        "unknown_time": "Unknown Time",
        "event": "Event",
        "no_evidence_summary": "No evidence summary.",
        "strategic_signal": "Strategic signal",
        "load_failed": "Failed to load artifacts: {error}",
        "missing_status": "Missing analyze_status.json. Graph and timeline may be incomplete.",
        "source_document": "Source Document",
        "model_config_path": "Model Config Path",
        "status_snapshot_date": "Status Snapshot Date",
        "cta_start": "Start Analysis",
        "generating": "Generating...",
        "missing_artifacts": "Artifacts are not generated for this case yet.",
        "generation_failed": "Generation failed: {error}",
        "cta_again": "Analysis Again",
        "starting": "Generating...",
        "progress_step1": "Step 1 complete · Ontologies ready",
        "progress_step2": "Step 2 complete · Timeline loaded",
        "progress_done": "Omen complete",
        "progress_stopped": "Analysis stopped",
        "pipeline_done_note": "Omen pipeline completed: ontologies, timeline, and persona generated.",
        "pipeline_failed": "Omen failed: {error}",
    },
    "zh": {
        "language_selector": "Language / 语言",
        "sidebar_title": "Omen 战略推演引擎",
        "sidebar_intro": "Omen 是一个开源的战略推演引擎，帮助决策者理清复杂现象背后的逻辑，不仅提供结论，更提供可追溯、可解释、可推演的战略洞察。",
        "no_cases_found": "未找到 cases/actors/*.md",
        "case_context": "选择案例",
        "settings": "设置",
        "output_root": "输出根目录",
        "page_title": "战略行动者研究",
        "page_intro": "只需一份案例，即可以一键洞察战略者核心信念、行动动机、关键事件和密切的影响关系。",
        "pipeline_title": "自动化流程",
        "step1_title": "构建本体",
        "step1_copy": "生成战略本体与行动者本体。",
        "step2_title": "提取事实",
        "step2_copy": "包括事件、关系与时间线。",
        "step3_title": "深度洞察",
        "step3_copy": "生成人物画像、决策特质与影响关系图。",
        "badge_done": "已完成",
        "badge_pending": "待完成",
        "deep_insight": "关键洞察",
        "tab_persona": "👤 战略画像",
        "actor_persona": "背景故事",
        "no_persona": "未找到战略画像，请先执行 `omen analyze actor --doc <name>`。",
        "no_narrative": "暂无叙事内容。",
        "key_traits": "关键特质",
        "no_traits": "暂无关键特质。",
        "influence_graph": "影响关系图",
        "timeline": "时间线",
        "no_timeline": "当前状态筛选下没有时间线事件。",
        "unknown_time": "未知时间",
        "event": "事件",
        "no_evidence_summary": "暂无证据摘要。",
        "strategic_signal": "战略信号",
        "load_failed": "加载产物失败：{error}",
        "missing_status": "缺少 analyze_status.json，图谱与时间线可能不完整。",
        "source_document": "源文档",
        "model_config_path": "模型配置路径",
        "status_snapshot_date": "状态快照日期",
        "cta_start": "开始分析",
        "generating": "生成中...",
        "missing_artifacts": "该案例尚未生成产物。",
        "generation_failed": "生成失败：{error}",
        "cta_again": "重新分析",
        "starting": "生成中...",
        "progress_step1": "第 1 步完成 · 本体已生成",
        "progress_step2": "第 2 步完成 · 时间线已生成",
        "progress_done": "Omen 已完成",
        "progress_stopped": "分析已停止",
        "pipeline_done_note": "Omen 流程已完成：本体、时间线和人物画像均已生成。",
        "pipeline_failed": "Omen 执行失败：{error}",
    },
}


def _t(key: str, **kwargs: Any) -> str:
    lang = str(st.session_state.get("spec7_ui_lang", "zh"))
    bundle = UI_TEXT.get(lang, UI_TEXT["en"])
    fallback = UI_TEXT["en"].get(key, key)
    text = bundle.get(key, fallback)
    return text.format(**kwargs) if kwargs else text


def _inject_app_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --omen-ink: #172033;
            --omen-muted: #5b6475;
            --omen-line: rgba(23, 32, 51, 0.10);
            --omen-accent: #0f766e;
            --omen-accent-soft: rgba(15, 118, 110, 0.10);
        }
        .omen-step-card {
            min-height: 170px;
            padding: 0.95rem 1rem;
            border-radius: 18px;
            border: 1px solid var(--omen-line);
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
            margin-bottom: 0.5rem;
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


def _list_actor_case_ids(cases_root: str | Path = "cases/actors") -> list[str]:
    root = Path(cases_root)
    if not root.exists():
        return []
    return sorted(p.stem for p in root.glob("*.md"))


def _artifact_paths(case_id: str, output_root: str | Path) -> dict[str, Path]:
    case_dir = actor_output_dir(case_id, output_root=output_root)
    return {
        "root": case_dir,
        "strategy": case_dir / STRATEGY_ONTOLOGY_FILENAME,
        "actor": case_dir / ACTOR_ONTOLOGY_FILENAME,
        "persona": case_dir / "analyze_persona.json",
        "status": case_dir / "analyze_status.json",
        "generation": case_dir / "generation.json",
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _suggest_actor_document_path(case_id: str) -> str:
    return str(Path("cases/actors") / f"{normalize_case_id(case_id)}.md")


def _run_actor_pipeline(
    *,
    case_id: str,
    title: str,
    document_path: str,
    known_outcome: str,
    config_path: str,
    status_date: str,
    output_root: str,
    progress_bar: Any | None = None,
    output_language: str = "en",
) -> None:
    case_dir = ensure_actor_output_dir(case_id, output_root=output_root)
    generation = generate_strategy_ontology_from_document(
        document_path=document_path,
        case_id=case_id,
        title=title,
        strategy=None,
        known_outcome=known_outcome,
        config_path=config_path,
        require_embeddings=False,
        use_embeddings=False,
    )
    known_outcome_effective = generation.inferred_known_outcome or known_outcome

    actor_payload, timeline_events = generate_actor_and_events_from_document(
        document_path=document_path,
        case_id=case_id,
        title=title,
        known_outcome=known_outcome_effective,
        config_path=config_path,
    )

    strategy_payload = attach_timeline_events(generation.strategy_ontology, timeline_events)
    strategy_payload = attach_actor_ref(
        strategy_payload,
        actor_payload,
        actor_filename=ACTOR_ONTOLOGY_FILENAME,
    )

    strategy_path = case_dir / STRATEGY_ONTOLOGY_FILENAME
    actor_path = case_dir / ACTOR_ONTOLOGY_FILENAME
    status_path = case_dir / "analyze_status.json"
    persona_path = case_dir / "analyze_persona.json"

    save_strategy_ontology(strategy_payload, strategy_path)
    actor_path.write_text(json.dumps(actor_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    st.session_state["spec7_pipeline_progress"] = 34
    if progress_bar is not None:
        progress_bar.progress(34, text=_t("progress_step1"))

    parsed_date = status_date.strip() or None
    status_payload = build_events_snapshot(
        strategy_ontology=strategy_payload,
        founder_ontology=actor_payload,
        year=None,
        date=parsed_date,
    )
    status_path.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    st.session_state["spec7_pipeline_progress"] = 67
    if progress_bar is not None:
        progress_bar.progress(67, text=_t("progress_step2"))

    persona_payload = generate_persona_insight(
        case_id=case_id,
        founder_ontology=actor_payload,
        strategy_ontology=strategy_payload,
        config_path=config_path,
        output_language=output_language,
    )
    persona_path.write_text(json.dumps(persona_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    st.session_state["spec7_pipeline_progress"] = 100
    if progress_bar is not None:
        progress_bar.progress(100, text=_t("progress_done"))

    report = {
        "case_id": case_id,
        "strategy_ontology_path": str(strategy_path),
        "actor_ontology_path": str(actor_path),
        "validation_passed": generation.validation_passed,
        "validation_issues": generation.validation_issues,
        "reused_existing": False,
    }
    (case_dir / "generation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    st.session_state["spec7_output_note"] = _t("pipeline_done_note")


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
                "time": str(row.get("time") or row.get("date") or _t("unknown_time")),
                "name": str(row.get("name") or row.get("event") or _t("event")),
                "description": str(
                    row.get("description")
                    or row.get("content")
                    or row.get("summary")
                    or row.get("event_excerpt")
                    or row.get("evidence")
                    or ""
                ),
                "strategic": bool(row.get("is_strategy_related", row.get("strategic", True))),
            }
        )
    return normalized


def _render_timeline_cards(timeline_rows: list[dict[str, Any]]) -> None:
    if not timeline_rows:
        st.info(_t("no_timeline"))
        return

    items: list[str] = []
    for row in timeline_rows:
        if not isinstance(row, dict):
            continue
        time_text = html.escape(str(row.get("time") or _t("unknown_time")))
        name_text = html.escape(str(row.get("name") or _t("event")))
        evidence_text = html.escape(str(row.get("description") or _t("no_evidence_summary")))
        badge = (
            f'<div class="omen-badge">{html.escape(_t("strategic_signal"))}</div>'
            if bool(row.get("strategic", True))
            else ""
        )
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

    st.markdown('<div class="omen-timeline">' + "".join(items) + "</div>", unsafe_allow_html=True)


def _render_workflow(paths: dict[str, Path]) -> None:
    st.markdown(f"#### {_t('pipeline_title')}")
    cards = [
        ("01", _t("step1_title"), _t("step1_copy"), paths["strategy"].exists() and paths["actor"].exists()),
        ("02", _t("step2_title"), _t("step2_copy"), paths["status"].exists()),
        ("03", _t("step3_title"), _t("step3_copy"), paths["persona"].exists()),
    ]
    cols = st.columns(3)
    for col, (num, title, copy, done) in zip(cols, cards):
        with col:
            badge = _t("badge_done") if done else _t("badge_pending")
            st.markdown(
                textwrap.dedent(
                    f"""
                    <div class="omen-step-card">
                        <div class="omen-step-number">{num}</div>
                        <div class="omen-step-title">{title}</div>
                        <div class="omen-step-copy">{copy}</div>
                        <div class="omen-step-badge">{badge}</div>
                    </div>
                    """
                ).strip(),
                unsafe_allow_html=True,
            )


def _render_persona(persona_payload: dict[str, Any] | None) -> None:
    if not isinstance(persona_payload, dict):
        st.info(_t("no_persona"))
        return

    insight = persona_payload.get("persona_insight")
    if not isinstance(insight, dict):
        st.info(_t("no_persona"))
        return

    left_col, right_col = st.columns([1.0, 1.0])

    with left_col:
        st.markdown(f"#### {_t('actor_persona')}")
        narrative = str(insight.get("narrative") or "").strip()
        st.write(narrative or _t("no_narrative"))

    with right_col:
        st.markdown(f"#### {_t('key_traits')}")
        _render_trait_cards(insight.get("key_traits"))


def _render_trait_cards(key_traits: Any) -> None:
    if not isinstance(key_traits, list) or not key_traits:
        st.caption(_t("no_traits"))
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


def _render_graph(status_payload: dict[str, Any] | None, actor_payload: dict[str, Any] | None) -> None:
    graph_source = status_payload if isinstance(status_payload, dict) else actor_payload
    if not isinstance(graph_source, dict):
        st.info(_t("missing_status"))
        return

    figure = build_actor_graph_figure(graph_source)
    figure.update_layout(title="Strategic Actor Graph")
    st.plotly_chart(figure, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Strategic Actor", layout="wide")
    _inject_app_styles()

    with st.sidebar:
        st.selectbox(
            _t("language_selector"),
            options=["zh", "en"],
            format_func=lambda code: "中文" if code == "zh" else "English",
            key="spec7_ui_lang",
        )
        st.markdown(f"## {_t('sidebar_title')}")
        st.caption(_t("sidebar_intro"))

    case_ids = _list_actor_case_ids()

    with st.sidebar:
        if case_ids:
            selected_case = st.selectbox(_t("case_context"), case_ids)
        else:
            selected_case = st.selectbox(
                _t("case_context"),
                options=[""],
                index=0,
                format_func=lambda _value: "-",
                disabled=True,
            )
            st.caption(_t("no_cases_found"))
        with st.expander(_t("settings"), expanded=False):
            output_root = st.text_input(_t("output_root"), value="output/actors")
            default_doc = _suggest_actor_document_path(selected_case) if selected_case else "cases/actors/<doc>.md"
            document_path = st.text_input(_t("source_document"), value=default_doc)
            config_path = st.text_input(_t("model_config_path"), value="config/llm.toml")
            status_date = st.text_input(_t("status_snapshot_date"), value="")

    effective_case_id = normalize_case_id(selected_case) if selected_case else "__no_case__"
    paths = _artifact_paths(effective_case_id, output_root)
    actor_payload = _read_json(paths["actor"])
    strategy_payload = _read_json(paths["strategy"])
    persona_payload = _read_json(paths["persona"])
    status_payload = _read_json(paths["status"])

    st.title(_t("page_title"))
    st.caption(_t("page_intro"))
    if selected_case:
        st.header(case_display_title(normalize_case_id(selected_case)))

    _render_workflow(paths)

    if not case_ids:
        return

    artifacts_ready = bool(actor_payload and strategy_payload)
    if not artifacts_ready:
        st.markdown('<div class="omen-cta-spacer"></div>', unsafe_allow_html=True)
        progress_placeholder = st.empty()
        show_runtime_status = st.session_state.spec7_pipeline_running or st.session_state.spec7_pipeline_progress > 0

        start_clicked = st.button(
            _t("cta_start"),
            type="primary",
            use_container_width=True,
            disabled=st.session_state.spec7_pipeline_running,
        )

        if start_clicked and not st.session_state.spec7_pipeline_running:
            st.session_state.spec7_pipeline_running = True
            st.session_state.spec7_pipeline_autorun = True
            st.session_state.spec7_pipeline_progress = 0
            st.session_state.spec7_output_note = ""
            st.rerun()

        if st.session_state.spec7_pipeline_running and st.session_state.spec7_pipeline_autorun:
            progress_bar = progress_placeholder.progress(10, text=_t("starting"))
            try:
                _run_actor_pipeline(
                    case_id=normalize_case_id(selected_case),
                    title=case_display_title(normalize_case_id(selected_case)),
                    document_path=document_path,
                    known_outcome=suggest_known_outcome(selected_case),
                    config_path=config_path,
                    status_date=status_date,
                    output_root=output_root,
                    progress_bar=progress_bar,
                    output_language=str(st.session_state.get("spec7_ui_lang", "zh")),
                )
            except Exception as exc:
                st.session_state.spec7_pipeline_progress = 100
                progress_bar.progress(100, text=_t("progress_stopped"))
                st.session_state.spec7_output_note = _t("pipeline_failed", error=str(exc))
            finally:
                st.session_state.spec7_pipeline_running = False
                st.session_state.spec7_pipeline_autorun = False
                st.rerun()
        elif show_runtime_status:
            progress_placeholder.progress(st.session_state.spec7_pipeline_progress)

        if st.session_state.spec7_output_note:
            st.info(st.session_state.spec7_output_note)
        return

    st.subheader(_t("deep_insight"))
    (tab_persona,) = st.tabs([_t("tab_persona")])
    with tab_persona:
        _render_persona(persona_payload)

    st.divider()
    st.subheader(_t("influence_graph"))
    _render_graph(status_payload, actor_payload)

    st.divider()
    st.subheader(_t("timeline"))
    timeline_rows = extract_timeline_rows(status_payload or {})
    _render_timeline_cards(timeline_rows)


if __name__ == "__main__":
    main()
