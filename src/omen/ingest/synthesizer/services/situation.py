"""Service layer for situation pipeline orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.ingest.processor import fetch_url_text, save_url_source_text
from omen.ingest.synthesizer.services.actor import ensure_actor_artifacts, ensure_persona_artifact_for_actor_ref
from omen.ingest.writer.markdown import save_situation_brief, save_situation_case_from_source
from omen.ingest.validators.situation import validate_situation_artifact_or_raise
from omen.ingest.validators.situation import validate_situation_source_or_raise
from omen.ui.artifacts import ACTOR_ONTOLOGY_FILENAME

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
        "or omit --actor to auto-build and link a strategic actor from the situation case"
    )


def _resolve_actor_ref_for_analysis(*, actor: str | None, input_path: Path) -> str:
    if actor is not None:
        return _validate_explicit_actor_ref(actor)

    print("No explicit actor provided; building strategic actor from situation case...")
    _case_id, case_dir = ensure_actor_artifacts(
        doc=str(input_path),
        title=None,
        known_outcome=None,
        config_path="config/llm.toml",
        output_dir="output/actors",
    )
    actor_path = case_dir / ACTOR_ONTOLOGY_FILENAME
    if not actor_path.exists():
        raise ValueError(f"auto-generated actor artifact not found: {actor_path}")
    print(f"Actor context auto-linked: {actor_path}")
    return str(actor_path)


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


def _analyze_and_save_situation(
    *,
    situation_file: str | Path,
    actor_ref: str | None,
    pack_id: str,
    pack_version: str,
    output_path: str | Path,
) -> None:
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


def run_situation_analysis(
    *,
    doc: str | None,
    input_alias: str | None,
    url: str | None,
    actor: str | None,
    output: str | None,
    pack_id: str | None,
    pack_version: str,
    force: bool = False,
) -> None:
    if url and (doc or input_alias):
        raise ValueError("use either --doc or --url, not both")

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
        validate_situation_source_or_raise(input_path)

    effective_actor_ref = _resolve_actor_ref_for_analysis(actor=actor, input_path=input_path)

    effective_pack_id = str(pack_id) if pack_id else _derive_default_pack_id(input_path, actor_ref=effective_actor_ref)
    output_path = Path(output) if output else _resolve_default_output_path(effective_pack_id)

    actor_path = Path(effective_actor_ref)
    if not actor_path.is_absolute():
        actor_path = Path.cwd() / actor_path
    persona_path = actor_path.parent / "analyze_persona.json"

    if not force:
        has_situation = output_path.exists()
        has_actor = actor_path.exists()
        has_persona = persona_path.exists()

        print(
            "Local artifact check: "
            f"situation={has_situation}, actor={has_actor}, persona={has_persona}"
        )
        if has_situation and has_actor and has_persona:
            print("Local-first: all required artifacts already exist, skip LLM generation.")
            return

    _analyze_and_save_situation(
        situation_file=input_path,
        actor_ref=effective_actor_ref,
        pack_id=effective_pack_id,
        pack_version=pack_version,
        output_path=output_path,
    )

    # Persona insight must run after situation analysis completes, so actor-enhanced context is ready.
    persona_path = ensure_persona_artifact_for_actor_ref(
        actor_ref=effective_actor_ref,
        config_path="config/llm.toml",
    )
    if persona_path is not None:
        print(f"Persona insight ensured: {persona_path}")


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

    # Explicit path input: path-like string or direct json filename.
    if "/" in raw or raw.endswith(".json"):
        return Path(raw)

    # Pack-id input: resolve to pack root situation artifact.
    return Path("data/scenarios") / raw / "situation.json"
