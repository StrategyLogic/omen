"""Service layer for situation pipeline orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.ingest.processor import fetch_url_text, save_url_source_text
from omen.ingest.reporter.markdown import save_situation_brief
from omen.ingest.validators.situation import validate_situation_artifact_or_raise

from omen.ingest.synthesizer.builders import situation as _builder


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


def _resolve_default_output_path(pack_id: str) -> Path:
    return Path("data/scenarios") / pack_id / "situation.json"


def _resolve_generated_case_path(case_name: str) -> Path:
    return Path("cases/situations") / f"{case_name}.md"


def validate_situation_source_or_raise(situation_file: str | Path) -> None:
    _builder.validate_situation_source_or_raise(situation_file)


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
    validated = validate_situation_artifact_or_raise(artifact)
    markdown_path = save_situation_brief(artifact_path.with_suffix(".md"), validated.model_dump())

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


def analyze_and_save_situation_from_url(
    *,
    url: str,
    actor_ref: str | None,
    pack_id: str | None,
    pack_version: str,
    output_path: str | Path | None,
) -> dict[str, Any]:
    source_text = fetch_url_text(url)
    source_text_path = save_url_source_text(url=url, text=source_text)

    case_name, case_markdown = _builder.generate_situation_case_document(
        source_text=source_text,
        source_ref=url,
        source_text_path=str(source_text_path),
    )
    generated_case_path = _resolve_generated_case_path(case_name)
    generated_case_path.parent.mkdir(parents=True, exist_ok=True)
    generated_case_path.write_text(case_markdown, encoding="utf-8")

    validate_situation_source_or_raise(generated_case_path)

    effective_pack_id = str(pack_id) if pack_id else _derive_default_pack_id(generated_case_path, actor_ref=actor_ref)
    effective_output_path = Path(output_path) if output_path is not None else _resolve_default_output_path(effective_pack_id)

    result = analyze_and_save_situation(
        situation_file=generated_case_path,
        actor_ref=actor_ref,
        pack_id=effective_pack_id,
        pack_version=pack_version,
        output_path=effective_output_path,
    )
    result.update(
        {
            "source_text_path": source_text_path,
            "generated_case_path": generated_case_path,
            "pack_id": effective_pack_id,
        }
    )
    return result


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
