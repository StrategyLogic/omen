"""Service layer for situation pipeline orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.ingest.processor import fetch_url_text, save_url_source_text
from omen.ingest.writer.markdown import save_situation_brief, save_situation_case_from_source
from omen.ingest.validators.situation import validate_situation_artifact_or_raise
from omen.ingest.validators.situation import validate_situation_source_or_raise

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


def _resolve_situation_doc_path(raw_doc: str) -> Path:
    raw = str(raw_doc).strip()
    if "/" in raw:
        candidate = Path(raw)
        if not candidate.suffix:
            candidate = candidate.with_suffix(".md")
        return candidate

    stem = raw[:-3] if raw.endswith(".md") else raw
    return Path("cases/situations") / f"{stem}.md"


def _validate_explicit_actor_ref(actor_ref: str) -> str:
    raw = str(actor_ref or "").strip()
    if not raw:
        raise ValueError("actor reference is empty")

    candidate = Path(raw)
    if candidate.exists():
        return raw

    cases_candidate = Path("cases") / raw
    if cases_candidate.exists():
        return str(cases_candidate)

    raise ValueError(
        "actor reference not found. Pass an existing actor artifact path with --actor, "
        "or omit --actor for decoupled situation analysis"
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


def analyze_and_save_situation(
    *,
    situation_file: str | Path,
    actor_ref: str | None,
    pack_id: str,
    pack_version: str,
    output_path: str | Path,
) -> dict[str, Any]:
    print(f"Situation source validation: {situation_file}")
    validate_situation_source_or_raise(situation_file)

    if actor_ref:
        print(f"Actor context enabled: {actor_ref}")

    print("Running LLM situation extraction and enhancement...")
    artifact = analyze_situation_document(
        situation_file=situation_file,
        actor_ref=actor_ref,
        pack_id=pack_id,
        pack_version=pack_version,
    )

    if actor_ref and isinstance(artifact.get("context"), dict):
        artifact["context"]["actor_ref"] = actor_ref

    print("Persisting situation artifacts...")
    artifact_path = save_situation_artifact(output_path, artifact)
    validated = validate_situation_artifact_or_raise(artifact)
    markdown_path = save_situation_brief(artifact_path.with_suffix(".md"), validated.model_dump())

    generation_trace_path = artifact_path.parent / "generation" / "log.json"
    generation_trace_payload = _builder.build_situation_confidence_trace(
        situation_artifact=artifact,
        situation_artifact_path=artifact_path,
    )
    save_auxiliary_json(generation_trace_path, generation_trace_payload)

    print(f"Situation artifact saved: {artifact_path}")
    print(f"Situation brief saved: {markdown_path}")
    print(f"Situation trace saved: {generation_trace_path}")

    return {
        "situation_artifact": artifact,
        "artifact_path": artifact_path,
        "markdown_path": markdown_path,
        "generation_trace_path": generation_trace_path,
    }


def run_situation_analysis(
    *,
    doc: str | None,
    input_alias: str | None,
    url: str | None,
    actor: str | None,
    output: str | None,
    pack_id: str | None,
    pack_version: str,
) -> dict[str, Any]:
    if url and (doc or input_alias):
        raise ValueError("use either --doc or --url, not both")

    effective_actor_ref = _validate_explicit_actor_ref(actor) if actor is not None else None
    source_text_path: Path | None = None
    generated_case_path: Path | None = None

    if url:
        print(f"URL fetch started: {url}")
        source_text = fetch_url_text(str(url))
        source_text_path = save_url_source_text(url=str(url), text=source_text)
        print(f"URL source saved: {source_text_path}")
        generated_case_path = save_situation_case_from_source(
            source_text=source_text,
            source_ref=str(url),
            source_text_path=str(source_text_path),
        )
        print(f"Situation case generated: {generated_case_path}")
        validate_situation_source_or_raise(generated_case_path)
        input_path = generated_case_path
    else:
        raw_doc = doc or input_alias
        if not raw_doc:
            raise ValueError("missing required argument --doc or --url")

        input_path = _resolve_situation_doc_path(str(raw_doc))
        if not input_path.exists():
            raise ValueError(f"input not found: {input_path}")

    effective_pack_id = str(pack_id) if pack_id else _derive_default_pack_id(input_path, actor_ref=effective_actor_ref)
    output_path = Path(output) if output else _resolve_default_output_path(effective_pack_id)

    result = analyze_and_save_situation(
        situation_file=input_path,
        actor_ref=effective_actor_ref,
        pack_id=effective_pack_id,
        pack_version=pack_version,
        output_path=output_path,
    )
    if source_text_path is not None and generated_case_path is not None:
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
