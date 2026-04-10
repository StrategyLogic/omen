"""Service layer for situation pipeline orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.ingest.reporter.markdown import render_situation_brief
from omen.ingest.validators.situation import validate_situation_artifact_or_raise

from omen.ingest.synthesizer.builders import situation as _builder

def validate_situation_source_or_raise(situation_file: str | Path) -> None:
    _builder.validate_situation_source_or_raise(situation_file)


def generate_situation_case_document(
    *,
    source_text: str,
    source_ref: str,
    source_text_path: str,
) -> tuple[str, str]:
    return _builder.generate_situation_case_document(
        source_text=source_text,
        source_ref=source_ref,
        source_text_path=source_text_path,
    )


def analyze_situation_document(
    *,
    situation_file: str | Path,
    actor_ref: str | None,
    pack_id: str,
    pack_version: str,
) -> dict[str, Any]:
    return _builder.analyze_situation_document(
        situation_file=situation_file,
        actor_ref=actor_ref,
        pack_id=pack_id,
        pack_version=pack_version,
    )


def load_situation_artifact(path: str | Path) -> dict[str, Any]:
    situation_path = Path(path)
    with situation_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    validated = validate_situation_artifact_or_raise(payload)
    return validated.model_dump()


def save_situation_artifact(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    validated = validate_situation_artifact_or_raise(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(validated.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def _save_situation_markdown(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    validated = validate_situation_artifact_or_raise(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_situation_brief(validated.model_dump())
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def analyze_and_save_situation(
    *,
    situation_file: str | Path,
    actor_ref: str | None,
    pack_id: str,
    pack_version: str,
    output_path: str | Path,
) -> dict[str, Any]:
    artifact = analyze_situation_document(
        situation_file=situation_file,
        actor_ref=actor_ref,
        pack_id=pack_id,
        pack_version=pack_version,
    )

    if actor_ref and isinstance(artifact.get("context"), dict):
        artifact["context"]["actor_ref"] = actor_ref

    artifact_path = save_situation_artifact(output_path, artifact)
    markdown_path = _save_situation_markdown(artifact_path.with_suffix(".md"), artifact)

    generation_trace_path = artifact_path.parent / "generation" / "log.json"
    generation_trace_payload = _builder.build_situation_confidence_trace(
        situation_artifact=artifact,
        situation_artifact_path=artifact_path,
    )
    save_auxiliary_json(generation_trace_path, generation_trace_payload)

    return {
        "situation_artifact": artifact,
        "artifact_path": artifact_path,
        "markdown_path": markdown_path,
        "generation_trace_path": generation_trace_path,
    }


def save_auxiliary_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def resolve_situation_artifact_ref(ref: str | Path) -> Path:
    raw = str(ref).strip()
    if not raw:
        raise ValueError("empty situation reference")

    candidate = Path(raw)
    if candidate.exists():
        return candidate

    root_candidate = Path("data/scenarios") / raw / "situation.json"
    if root_candidate.exists():
        return root_candidate

    return Path("data/scenarios") / raw / "generation" / "situation.json"
