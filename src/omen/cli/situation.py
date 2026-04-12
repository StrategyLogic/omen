"""Situation analysis CLI commands."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from omen.ingest.synthesizer.services.scenario import (
    save_scenario_ontology_markdown,
    save_scenario_ontology_slice,
)
from omen.scenario.planner import from_situation
from omen.scenario.planner import ScenarioDecompositionValidationError
from omen.ingest.synthesizer.services.errors import LLMJsonValidationAbort
from omen.ingest.synthesizer.services.situation import (
    load_situation_artifact,
    resolve_situation_artifact_ref,
    run_situation_analysis,
    save_auxiliary_json,
)
from omen.scenario.ingest_validator import DeferredScopeFeatureError


def _resolve_situation_doc_path(raw_doc: str) -> Path:
    raw = str(raw_doc).strip()
    if "/" in raw:
        candidate = Path(raw)
        if not candidate.suffix:
            candidate = candidate.with_suffix(".md")
        return candidate

    stem = raw[:-3] if raw.endswith(".md") else raw
    return Path("cases/situations") / f"{stem}.md"


def _derive_case_name_from_path(input_path: Path) -> str:
    stem = input_path.stem.strip().lower()
    if stem.endswith("_situation"):
        stem = stem[: -len("_situation")]
    for separator in ("-", "_"):
        if separator in stem:
            head = stem.split(separator, 1)[0].strip()
            if head:
                return head
    return stem or "case"


def _derive_default_pack_id(input_path: Path, *, actor_ref: str | None) -> str:
    case_name = _derive_case_name_from_path(input_path)
    if actor_ref:
        return f"strategic_actor_{case_name}_v1"
    return f"{case_name}_v1"


def _resolve_default_output_path(_input_path: Path, pack_id: str) -> Path:
    return Path("data/scenarios") / pack_id / "situation.json"


def _validate_explicit_actor_ref(actor_ref: str) -> str:
    raw = str(actor_ref or "").strip()
    if not raw:
        raise ValueError("actor reference is empty")

    candidate = Path(raw)
    if candidate.exists():
        return raw

    # Backward compatibility: allow repo-relative actor refs like actors/*.md
    cases_candidate = Path("cases") / raw
    if cases_candidate.exists():
        return str(cases_candidate)

    raise ValueError(
        "actor reference not found. Pass an existing actor artifact path with --actor, "
        "or omit --actor to auto-build and link a strategic actor from the situation case"
    )


def _resolve_splitter_default_output_path(_situation_path: Path, pack_id: str) -> Path:
    return Path("data/scenarios") / pack_id / "scenario_pack.json"


def _resolve_scenario_generation_trace_path(scenario_output_path: Path) -> Path:
    return scenario_output_path.parent / "generation" / "log.json"


def _resolve_scenario_raw_output_path(scenario_output_path: Path) -> Path:
    return scenario_output_path.parent / "generation" / "output.txt"


def _resolve_scenario_failure_output_path(*, args: Any, output_path_arg: Path | None, situation_path: Path | None) -> Path:
    if output_path_arg is not None:
        return _resolve_scenario_raw_output_path(output_path_arg)

    if situation_path is not None and situation_path.suffix == ".json":
        if situation_path.parent.name == "generation":
            return situation_path.parent / "output.txt"
        return situation_path.parent / "generation" / "output.txt"

    raw_ref = str(args.situation).strip()
    if "/" not in raw_ref and not raw_ref.endswith(".json"):
        pack_id = str(args.pack_id or raw_ref)
        return Path("data/scenarios") / pack_id / "generation" / "output.txt"

    return Path("data/scenarios") / "unknown" / "generation" / "output.txt"


def _load_generation_trace_payload(trace_path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if trace_path.exists():
        try:
            loaded = json.loads(trace_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        except Exception:
            payload = {}

    payload.setdefault("artifact_type", "situation_generation_trace")
    history = payload.get("trace_history")
    if not isinstance(history, list):
        payload["trace_history"] = []
    return payload


def _append_trace_history_event(
    payload: dict[str, Any],
    *,
    stage: str,
    status: str,
    details: dict[str, Any],
) -> None:
    history = payload.get("trace_history")
    if not isinstance(history, list):
        history = []

    history.append(
        {
            "stage": stage,
            "status": status,
            "generated_at": datetime.now().isoformat(),
            **details,
        }
    )
    payload["trace_history"] = history


def _append_scenario_decomposition_trace(
    *,
    trace_path: Path,
    scenario_artifact_path: Path,
    situation_ref: Path,
    decomposition_quality: dict[str, Any] | None,
    planner_trace: dict[str, Any] | None = None,
) -> None:
    payload = _load_generation_trace_payload(trace_path)
    decomposition_entry = {
        "scenario_artifact_path": str(scenario_artifact_path),
        "situation_ref": str(situation_ref),
        "generated_at": datetime.now().isoformat(),
        "schema_completeness_percent": float((decomposition_quality or {}).get("schema_completeness_percent") or 0.0),
        "logic_usable": bool((decomposition_quality or {}).get("logic_usable", False)),
        "retries": int((decomposition_quality or {}).get("retries") or 0),
        "validation_issues": list((decomposition_quality or {}).get("validation_issues") or []),
        "logic_issues": list((decomposition_quality or {}).get("logic_issues") or []),
    }
    payload["scenario_decomposition"] = decomposition_entry
    if isinstance(planner_trace, dict):
        payload["scenario_planner"] = {
            "actor_style_enhancement": dict(planner_trace.get("actor_style_enhancement") or {}),
            "prior_scoring": dict(planner_trace.get("prior_scoring") or {}),
        }

    _append_trace_history_event(
        payload,
        stage="scenario_decomposition",
        status="ok",
        details={
            "scenario_artifact_path": str(scenario_artifact_path),
            "situation_ref": str(situation_ref),
            "schema_completeness_percent": decomposition_entry["schema_completeness_percent"],
            "logic_usable": decomposition_entry["logic_usable"],
            "retries": decomposition_entry["retries"],
        },
    )
    save_auxiliary_json(trace_path, payload)


def _write_non_json_llm_output(path: Path, *, stage: str, reason: str, raw_output: str, retry_output: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sections = [
        f"stage: {stage}",
        f"reason: {reason}",
        "",
        "[raw_output]",
        raw_output,
    ]
    if retry_output:
        sections.extend(["", "[retry_output]", retry_output])
    content = "\n".join(sections).rstrip() + "\n"
    path.write_text(content, encoding="utf-8")
    return path


def _write_scenario_failure_trace(
    *,
    trace_path: Path,
    situation_ref: Path | None,
    stage: str,
    reason: str,
) -> Path:
    payload = _load_generation_trace_payload(trace_path)
    payload["scenario_decomposition"] = {
        "scenario_artifact_path": "",
        "situation_ref": str(situation_ref) if situation_ref else "",
        "generated_at": datetime.now().isoformat(),
        "schema_completeness_percent": 0.0,
        "logic_usable": False,
        "retries": 0,
        "validation_issues": [reason],
        "logic_issues": [],
        "stage": stage,
        "status": "failed",
    }
    _append_trace_history_event(
        payload,
        stage=stage,
        status="failed",
        details={
            "situation_ref": str(situation_ref) if situation_ref else "",
            "reason": reason,
        },
    )
    save_auxiliary_json(trace_path, payload)
    return trace_path


def _update_situation_brief_completion_status(*, situation_ref: Path, completed_at: datetime) -> Path | None:
    brief_path = situation_ref.with_suffix(".md")
    if not brief_path.exists():
        return None

    status_line = (
        "**Status**: Completed. Deterministic A/B/C scenarios were generated at "
        f"{completed_at.strftime('%Y-%m-%d %H:%M')}."
    )

    original = brief_path.read_text(encoding="utf-8")
    lines = original.splitlines()
    updated: list[str] = []
    replaced = False
    skip_next = False

    for index, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        normalized = line.strip().lower().replace("**", "")
        if normalized.startswith("status:"):
            updated.append(status_line)
            replaced = True
            if index + 1 < len(lines):
                next_normalized = lines[index + 1].strip().lower().replace("**", "")
                if next_normalized.startswith("next step:"):
                    skip_next = True
            continue

        if replaced and normalized.startswith("next step:"):
            continue

        updated.append(line)

    if not replaced:
        if updated and updated[-1].strip():
            updated.append("")
        updated.append(status_line)

    brief_path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
    return brief_path


def _derive_pack_id_from_situation_artifact(situation_artifact: dict[str, Any], situation_path: Path) -> str:
    source_meta = situation_artifact.get("source_meta") or {}
    actor_ref = source_meta.get("actor_ref")
    source_path = source_meta.get("source_path")
    base_path = Path(str(source_path)) if source_path else situation_path
    return _derive_default_pack_id(base_path, actor_ref=str(actor_ref) if actor_ref else None)


def register_situation_analyze_commands(analyze_subparsers: Any) -> None:
    situation = analyze_subparsers.add_parser(
        "situation",
        help="analyze company situation documents into scenario ontology artifacts",
    )
    situation.add_argument(
        "--doc",
        required=False,
        help="Situation doc name or path. Bare names resolve to cases/situations/<doc>.md",
    )
    situation.add_argument(
        "--input",
        required=False,
        help="Deprecated alias for --doc",
    )
    situation.add_argument(
        "--url",
        required=False,
        help="One-step URL ingest: fetch source text, create cases/situations/<case>.md, then run analyze flow",
    )
    situation.add_argument(
        "--actor",
        required=False,
        help="Optional existing actor artifact path used as background context. Omit --actor to auto-build and link a strategic actor from the situation case",
    )
    situation.add_argument(
        "--output",
        required=False,
        help="Optional output path for generated situation JSON. Defaults to data/scenarios/<pack_id>/situation.json",
    )
    situation.add_argument(
        "--pack-id",
        required=False,
        default=None,
        help="Deterministic pack id for scenario slot policy",
    )
    situation.add_argument(
        "--pack-version",
        required=False,
        default="1.0.0",
        help="Deterministic pack version",
    )
    situation.add_argument(
        "--force",
        action="store_true",
        help="Force regenerate situation artifacts even if local artifacts already exist",
    )


def register_scenario_command(subparsers: Any) -> None:
    scenario = subparsers.add_parser(
        "scenario",
        help="split a situation document into fixed A/B/C scenarios",
    )
    scenario.add_argument(
        "--situation",
        required=True,
        help="Situation reference: pack_id or path to situation artifact JSON",
    )
    scenario.add_argument(
        "--output",
        required=False,
        help="Optional output JSON path. Defaults to data/scenarios/<pack_id>/<doc_stem>.json",
    )
    scenario.add_argument(
        "--pack-id",
        required=False,
        default=None,
        help="Deterministic pack id for scenario slot policy",
    )
    scenario.add_argument(
        "--pack-version",
        required=False,
        default="1.0.0",
        help="Deterministic pack version",
    )
    scenario.add_argument(
        "--actor",
        required=False,
        help="Optional actor reference used for planning query preparation",
    )


def handle_situation_analyze_command(args: Any) -> int:
    print("Situation analysis started")
    try:
        run_situation_analysis(
            doc=getattr(args, "doc", None),
            input_alias=getattr(args, "input", None),
            url=getattr(args, "url", None),
            actor=getattr(args, "actor", None),
            output=getattr(args, "output", None),
            pack_id=(
                str(getattr(args, "pack_id"))
                if getattr(args, "pack_id", None)
                else None
            ),
            pack_version=str(getattr(args, "pack_version", "1.0.0")),
            force=bool(getattr(args, "force", False)),
        )
        print("Situation analysis completed")
        return 0
    except DeferredScopeFeatureError as exc:
        print(f"Deferred scope: {exc}")
        print(
            "This release supports deterministic A/B/C packs only. "
            "Dynamic scenario authoring and enterprise resistance extensions are deferred."
        )
        return 2
    except LLMJsonValidationAbort as exc:
        print(
            "LLM JSON validation aborted by policy: "
            f"{exc.stage} -> {exc.reason}. Exiting without retry/fallback."
        )
        return 2
    except Exception as exc:
        print(f"Situation analysis failed: {exc}")
        return 2


def handle_scenario_command(args: Any) -> int:
    try:
        situation_path = resolve_situation_artifact_ref(str(args.situation))
        if not situation_path.exists():
            raise ValueError(f"situation artifact not found: {situation_path}")

        situation_artifact = load_situation_artifact(situation_path)
        if args.pack_id:
            pack_id = str(args.pack_id)
        elif "/" not in str(args.situation) and not str(args.situation).endswith(".json"):
            pack_id = str(args.situation)
        else:
            pack_id = _derive_pack_id_from_situation_artifact(situation_artifact, situation_path)

        actor_ref = str(args.actor).strip() if args.actor else ""
        if not actor_ref:
            actor_ref = str((situation_artifact.get("source_meta") or {}).get("actor_ref") or "unknown_actor")

        output_path_arg = (
            Path(args.output)
            if args.output
            else _resolve_splitter_default_output_path(situation_path, pack_id)
        )

        ontology = from_situation(
            situation_artifact=situation_artifact,
            pack_id=pack_id,
            pack_version=str(args.pack_version),
            actor_ref=actor_ref,
            traces_dir=output_path_arg.parent / "traces",
        )
        planner_trace = dict(ontology.pop("_planner_trace", {}) or {})

        output_path = save_scenario_ontology_slice(output_path_arg, ontology)
        markdown_path = output_path.with_suffix(".md")
        save_scenario_ontology_markdown(markdown_path, ontology)
        scenario_trace_path = _resolve_scenario_generation_trace_path(output_path)
        _append_scenario_decomposition_trace(
            trace_path=scenario_trace_path,
            scenario_artifact_path=output_path,
            situation_ref=situation_path,
            decomposition_quality=ontology.get("decomposition_quality"),
            planner_trace=planner_trace,
        )
        status_updated_path = _update_situation_brief_completion_status(
            situation_ref=situation_path,
            completed_at=datetime.now(),
        )
        print(f"Saved scenario planning artifact to {output_path}")
        print(f"Saved scenario planning summary to {markdown_path}")
        print(f"Updated generation trace with scenario decomposition quality: {scenario_trace_path}")
        if status_updated_path is not None:
            print(f"Updated situation brief status: {status_updated_path}")
        return 0
    except Exception as exc:
        output_path_arg = locals().get("output_path_arg")
        if isinstance(output_path_arg, Path):
            resolved_output_path = output_path_arg
        else:
            resolved_output_path = None

        resolved_situation_path = locals().get("situation_path")
        if isinstance(resolved_situation_path, Path):
            situation_ref_path = resolved_situation_path
        else:
            situation_ref_path = None

        output_dump = _resolve_scenario_failure_output_path(
            args=args,
            output_path_arg=resolved_output_path,
            situation_path=situation_ref_path,
        )

        if isinstance(exc, LLMJsonValidationAbort):
            stage = exc.stage
            reason = exc.reason
            raw_output = exc.raw_output
            retry_output = exc.retry_output
        elif isinstance(exc, ScenarioDecompositionValidationError):
            stage = "scenario_planning"
            reason = str(exc)
            raw_output = json.dumps(exc.decomposition_payload, ensure_ascii=False, indent=2)
            retry_output = ""
        elif isinstance(exc, DeferredScopeFeatureError):
            stage = "deferred_scope"
            reason = str(exc)
            raw_output = ""
            retry_output = ""
        else:
            stage = "scenario_planning"
            reason = str(exc)
            raw_output = ""
            retry_output = ""

        _write_non_json_llm_output(
            output_dump,
            stage=stage,
            reason=reason,
            raw_output=raw_output,
            retry_output=retry_output,
        )

        trace_path = output_dump.parent / "log.json"
        _write_scenario_failure_trace(
            trace_path=trace_path,
            situation_ref=situation_ref_path,
            stage=stage,
            reason=reason,
        )

        print(f"Scenario planning failed: {reason}")
        print(f"Scenario debug output saved to {output_dump}")
        print(f"Scenario generation trace saved to {trace_path}")
        return 2
