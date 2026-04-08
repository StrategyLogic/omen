"""Top-level strategic actor analysis commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.analysis.actor.insight import generate_persona_insight
from omen.analysis.actor.query import build_events_snapshot
from omen.ingest.synthesizer.services.actor import ensure_actor_artifacts
from omen.ingest.synthesizer.prompts.registry import ensure_analyze_prompt_available
from omen.ingest.validators.actor import (
    validate_actor_ontology_payload,
    validate_actor_strategy_link_payload,
)
from omen.ingest.validators.scenario import format_validation_report
from omen.ui.artifacts import (
  ACTOR_ONTOLOGY_FILENAME,
  STRATEGY_ONTOLOGY_FILENAME,
  ensure_actor_output_dir,
)
from omen.ui.case_catalog import normalize_case_id


ACTOR_DEFAULT_OUTPUT_ROOT = "output/actors"


def _add_actor_common_args(parser: Any) -> None:
  parser.add_argument(
    "--doc",
    required=False,
    help="Document name or path. Bare names resolve to cases/actors/<doc>.md",
  )
  parser.add_argument("--title", required=False, help="Optional case title")
  parser.add_argument("--known-outcome", required=False, help="Optional known outcome")
  parser.add_argument("--year", required=False, type=int, help="Optional status snapshot year")
  parser.add_argument("--date", required=False, help="Optional status snapshot date")
  parser.add_argument(
    "--config",
    required=False,
    default="config/llm.toml",
    help="Path to local LLM config TOML",
  )
  parser.add_argument(
    "--output-dir",
    required=False,
    default=ACTOR_DEFAULT_OUTPUT_ROOT,
    help="Root output directory for actor analysis artifacts",
  )


def register_analyze_commands(subparsers: Any) -> Any:
  analyze = subparsers.add_parser("analyze", help="top-level analysis commands")
  analyze_sub = analyze.add_subparsers(dest="analyze_object", required=True)

  actor = analyze_sub.add_parser("actor", help="strategic actor analysis flow")
  _add_actor_common_args(actor)

  actor_sub = actor.add_subparsers(dest="actor_command", required=False)
  persona = actor_sub.add_parser("persona", help="output persona only")
  _add_actor_common_args(persona)

  strategy = actor_sub.add_parser("strategy", help="cloud-only in OSS baseline")
  _add_actor_common_args(strategy)

  insight = actor_sub.add_parser("insight", help="cloud-only in OSS baseline")
  _add_actor_common_args(insight)

  founder = analyze_sub.add_parser("founder", help="deprecated founder analyze object")
  founder.add_argument("--doc", required=False)
  founder.add_argument("--title", required=False)
  founder.add_argument("--known-outcome", required=False)
  founder.add_argument("--year", required=False, type=int)
  founder.add_argument("--date", required=False)
  founder.add_argument("--config", required=False, default="config/llm.toml")
  founder.add_argument("--output-dir", required=False, default="output/founder")
  return analyze_sub


def register_validate_commands(subparsers: Any) -> None:
  validate = subparsers.add_parser("validate", help="validate artifact contracts")
  validate_sub = validate.add_subparsers(dest="validate_object", required=True)

  actor = validate_sub.add_parser("actor", help="validate actor artifacts")
  actor.add_argument(
      "--doc",
      required=False,
      help="Document name or path. Bare names resolve to case id by stem",
  )
  actor.add_argument("--file", required=False, help="Single file to validate")
  actor.add_argument("--output-dir", required=False, default=ACTOR_DEFAULT_OUTPUT_ROOT)


def _load_analysis_artifacts(case_id: str, output_dir: str) -> tuple[Path, dict[str, Any] | None, dict[str, Any]]:
  case_dir = ensure_actor_output_dir(case_id, output_root=output_dir)
  strategy_path = case_dir / STRATEGY_ONTOLOGY_FILENAME
  actor_path = case_dir / ACTOR_ONTOLOGY_FILENAME

  if not actor_path.exists():
    raise FileNotFoundError(f"missing actor artifact: {actor_path}")

  actor_payload = json.loads(actor_path.read_text(encoding="utf-8"))
  strategy_payload = None
  if strategy_path.exists():
    strategy_payload = json.loads(strategy_path.read_text(encoding="utf-8"))
  return case_dir, strategy_payload, actor_payload


def _run_status(
  case_dir: Path,
  strategy_payload: dict[str, Any] | None,
  actor_payload: dict[str, Any],
  *,
  year: int | None,
  date: str | None,
) -> None:
  if strategy_payload is None:
    raise ValueError("Missing strategy ontology for status analysis")

  status_payload = build_events_snapshot(
    strategy_ontology=strategy_payload,
    actor_ontology=actor_payload,
    year=year,
    date=date,
  )
  output_path = case_dir / "analyze_status.json"
  output_path.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2), encoding="utf-8")
  print(f"Saved analyze status payload to {output_path}")


def _run_persona(
  case_id: str,
  case_dir: Path,
  strategy_payload: dict[str, Any] | None,
  actor_payload: dict[str, Any],
  config_path: str,
) -> None:
  ensure_analyze_prompt_available("persona")
  persona_payload = generate_persona_insight(
    case_id=case_id,
    actor_ontology=actor_payload,
    strategy_ontology=strategy_payload,
    config_path=config_path,
  )
  output_path = case_dir / "analyze_persona.json"
  output_path.write_text(json.dumps(persona_payload, ensure_ascii=False, indent=2), encoding="utf-8")
  print(f"Saved analyze persona payload to {output_path}")


def handle_analyze_command(args: Any) -> int:
  if args.analyze_object != "actor":
    print(f"Analyze object `{args.analyze_object}` is not supported")
    return 3

  actor_command = getattr(args, "actor_command", None)

  if not getattr(args, "doc", None):
    print("Analyze actor requires --doc <name_or_path>")
    return 2

  try:
    case_id, _ = ensure_actor_artifacts(
      doc=str(args.doc),
      title=str(args.title) if args.title else None,
      known_outcome=str(args.known_outcome) if args.known_outcome else None,
      config_path=str(args.config),
      output_dir=str(args.output_dir),
    )
    case_dir, strategy_payload, actor_payload = _load_analysis_artifacts(case_id, args.output_dir)
  except Exception as exc:
    print(f"Analyze actor setup failed: {exc}")
    return 2

  try:
    if actor_command in (None, ""):
      _run_status(case_dir, strategy_payload, actor_payload, year=args.year, date=args.date)
      _run_persona(case_id, case_dir, strategy_payload, actor_payload, args.config)
      print("Completed actor research workflow")
      return 0

    if actor_command == "persona":
      _run_persona(case_id, case_dir, strategy_payload, actor_payload, args.config)
      return 0

    print(f"Analyze actor sub-command `{actor_command}` is not supported")
    return 3
  except Exception as exc:
    print(f"Analyze actor failed: {exc}")
    return 2


def _issues_to_errors(issues: list[Any], *, source: str) -> list[dict[str, Any]]:
  errors: list[dict[str, Any]] = []
  for issue in issues:
    errors.append(
      {
        "field": getattr(issue, "path", "unknown"),
        "reason": getattr(issue, "message", str(issue)),
        "source": source,
        "code": getattr(issue, "code", "validation_error"),
      }
    )
  return errors


def handle_validate_command(args: Any) -> int:
  if args.validate_object != "actor":
    print(f"Validate object `{args.validate_object}` is not supported")
    return 3

  if bool(args.doc) == bool(args.file):
    print("Provide exactly one of --doc or --file")
    return 2

  try:
    if args.file:
      path = Path(args.file)
      payload = json.loads(path.read_text(encoding="utf-8"))
      if path.name == ACTOR_ONTOLOGY_FILENAME:
        errors = _issues_to_errors(
          validate_actor_ontology_payload(payload),
          source=str(path),
        )
      else:
        errors = _issues_to_errors(
          validate_actor_strategy_link_payload(payload, expected_actor_filename=ACTOR_ONTOLOGY_FILENAME),
          source=str(path),
        )
      report = format_validation_report(target_artifact=str(path), errors=errors)
      print(json.dumps(report, ensure_ascii=False, indent=2))
      return 0 if report["status"] == "pass" else 2

    case_id = normalize_case_id(args.doc)
    case_dir = ensure_actor_output_dir(case_id, output_root=args.output_dir)
    actor_path = case_dir / ACTOR_ONTOLOGY_FILENAME
    strategy_path = case_dir / STRATEGY_ONTOLOGY_FILENAME
    errors: list[dict[str, Any]] = []
    if not actor_path.exists():
      errors.append({"field": ACTOR_ONTOLOGY_FILENAME, "reason": "missing file", "source": str(case_dir)})
    else:
      actor_payload = json.loads(actor_path.read_text(encoding="utf-8"))
      errors.extend(
        _issues_to_errors(
          validate_actor_ontology_payload(actor_payload),
          source=str(actor_path),
        )
      )
    if not strategy_path.exists():
      errors.append({"field": STRATEGY_ONTOLOGY_FILENAME, "reason": "missing file", "source": str(case_dir)})
    else:
      strategy_payload = json.loads(strategy_path.read_text(encoding="utf-8"))
      errors.extend(
        _issues_to_errors(
          validate_actor_strategy_link_payload(
            strategy_payload,
            expected_actor_filename=ACTOR_ONTOLOGY_FILENAME,
          ),
          source=str(strategy_path),
        )
      )

    report = format_validation_report(target_artifact=str(case_dir), errors=errors)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 2
  except Exception as exc:
      print(f"Validate actor failed: {exc}")
      return 2
