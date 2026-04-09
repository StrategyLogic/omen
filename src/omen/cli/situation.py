"""Situation analysis CLI commands."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from omen.ingest.processor import fetch_url_text, save_url_source_text
from omen.ingest.synthesizer.builders.situation import (
    validate_situation_source_or_raise,
)
from omen.scenario.loader import (
    load_situation_artifact,
    resolve_situation_artifact_ref,
    save_auxiliary_json,
    save_scenario_ontology_markdown,
    save_scenario_ontology_slice,
    save_situation_artifact,
    save_situation_markdown,
)
from omen.scenario.planner import plan_scenarios_from_situation
from omen.scenario.planner import ScenarioDecompositionValidationError
from omen.ingest.synthesizer.services.situation import (
    LLMJsonValidationAbort,
    analyze_situation_document,
    build_situation_confidence_trace,
    generate_situation_case_document,
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
        "or omit --actor for decoupled situation analysis"
    )


def _resolve_splitter_default_output_path(_situation_path: Path, pack_id: str) -> Path:
    return Path("data/scenarios") / pack_id / "scenario_pack.json"


def _resolve_generation_trace_output_path(situation_output_path: Path) -> Path:
    return situation_output_path.parent / "generation" / "log.json"


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


def _append_scenario_decomposition_trace(
    *,
    trace_path: Path,
    scenario_artifact_path: Path,
    situation_ref: Path,
    decomposition_quality: dict[str, Any] | None,
    planner_trace: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {}
    if trace_path.exists():
        try:
            payload = json.loads(trace_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}

    payload.setdefault("artifact_type", "situation_generation_trace")
    payload["scenario_decomposition"] = {
        "scenario_artifact_path": str(scenario_artifact_path),
        "situation_ref": str(situation_ref),
        "generated_at": datetime.now().isoformat(),
        "schema_completeness_percent": float((decomposition_quality or {}).get("schema_completeness_percent") or 0.0),
        "logic_usable": bool((decomposition_quality or {}).get("logic_usable", False)),
        "retries": int((decomposition_quality or {}).get("retries") or 0),
        "validation_issues": list((decomposition_quality or {}).get("validation_issues") or []),
        "logic_issues": list((decomposition_quality or {}).get("logic_issues") or []),
    }
    if isinstance(planner_trace, dict):
        payload["scenario_planner"] = {
            "actor_style_enhancement": dict(planner_trace.get("actor_style_enhancement") or {}),
            "prior_scoring": dict(planner_trace.get("prior_scoring") or {}),
        }
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
    payload: dict[str, Any] = {
        "artifact_type": "situation_generation_trace",
        "scenario_decomposition": {
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
        },
    }
    save_auxiliary_json(trace_path, payload)
    return trace_path


def _resolve_generated_case_path(case_name: str) -> Path:
    return Path("cases/situations") / f"{case_name}.md"


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
        help="Optional actor reference path or identifier used as background context",
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
        "--config",
        required=False,
        default="config/llm.toml",
        help="Path to local LLM config TOML",
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
    scenario.add_argument(
        "--config",
        required=False,
        default="config/llm.toml",
        help="Path to local LLM config TOML",
    )


def handle_situation_analyze_command(args: Any) -> int:
    try:
        if args.url and (args.doc or args.input):
            print("Analyze situation failed: use either --doc or --url, not both")
            return 2

        raw_doc = args.doc or args.input
        if args.url:
            print("Using URL source for situation analysis...")
            try:
                source_text = fetch_url_text(str(args.url))
                source_text_path = save_url_source_text(url=str(args.url), text=source_text)
                print(f"URL fetch: SUCCESS ({source_text_path})")
            except Exception as exc:
                print(f"URL fetch: ERROR ({exc})")
                print("Unable to fetch or extract readable text from the provided URL.")
                return 2

            try:
                print("LLM case generation from URL text...")
                case_name, case_markdown = generate_situation_case_document(
                    source_text=source_text,
                    source_ref=str(args.url),
                    source_text_path=str(source_text_path),
                    config_path=str(args.config),
                )
                generated_case_path = _resolve_generated_case_path(case_name)
                generated_case_path.parent.mkdir(parents=True, exist_ok=True)
                generated_case_path.write_text(case_markdown, encoding="utf-8")
                print(f"Generated situation case: SUCCESS ({generated_case_path})")
            except Exception as exc:
                print(f"LLM case generation: ERROR ({exc})")
                print("Unable to convert fetched URL text into a situation case document.")
                return 2

            raw_doc = str(generated_case_path)

        if not raw_doc:
            print("Analyze situation failed: missing required argument --doc or --url")
            return 2

        input_path = _resolve_situation_doc_path(str(raw_doc))
        if not input_path.exists():
            print(f"Analyze situation failed: input not found: {input_path}")
            return 2

        validate_situation_source_or_raise(input_path)
        effective_actor_ref = None
        if args.actor is not None:
            effective_actor_ref = _validate_explicit_actor_ref(str(args.actor))
        pack_id = str(args.pack_id) if args.pack_id else _derive_default_pack_id(input_path, actor_ref=effective_actor_ref)
        output_path_arg = (
            Path(args.output)
            if args.output
            else _resolve_default_output_path(input_path, pack_id)
        )

        if effective_actor_ref:
            print("Building scenario pack with strategic actor context...")

        situation_artifact = analyze_situation_document(
            situation_file=input_path,
            actor_ref=effective_actor_ref,
            pack_id=pack_id,
            pack_version=str(args.pack_version),
            config_path=str(args.config),
        )
        context = situation_artifact.get("context")
        if effective_actor_ref and isinstance(context, dict):
            context["actor_ref"] = effective_actor_ref
        output_path = save_situation_artifact(output_path_arg, situation_artifact)
        markdown_path = output_path.with_suffix(".md")
        save_situation_markdown(markdown_path, situation_artifact, config_path=str(args.config))
        generation_trace_path = _resolve_generation_trace_output_path(output_path)
        generation_trace_payload = build_situation_confidence_trace(
            situation_artifact=situation_artifact,
            situation_artifact_path=output_path,
        )
        save_auxiliary_json(generation_trace_path, generation_trace_payload)
        print(f"Saved situation artifact to {output_path}")
        print(f"Saved situation summary to {markdown_path}")
        print(f"Saved situation generation trace to {generation_trace_path}")
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
        print(f"Analyze situation failed: {exc}")
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

        ontology = plan_scenarios_from_situation(
            situation_artifact=situation_artifact,
            pack_id=pack_id,
            pack_version=str(args.pack_version),
            actor_ref=actor_ref,
            config_path=str(args.config),
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
        print(f"Saved scenario planning artifact to {output_path}")
        print(f"Saved scenario planning summary to {markdown_path}")
        print(f"Updated generation trace with scenario decomposition quality: {scenario_trace_path}")
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
