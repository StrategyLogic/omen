"""Actor insight surface (LLM-based generation)."""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import Any

import yaml

from omen.ingest.synthesizer.clients import create_chat_client
from omen.ingest.synthesizer.config import load_llm_config
from omen.ingest.synthesizer.prompts.registry import get_analyze_prompt_version_token
from omen.ingest.synthesizer.prompts import build_json_retry_prompt, build_persona_insight_prompt


def _normalize_output_language(value: str | None) -> str:
    lang = str(value or "").strip().lower()
    if lang.startswith("zh"):
        return "zh"
    return "en"


def _language_instruction(output_language: str) -> str:
    if output_language == "zh":
        return "Output language requirement: All natural-language fields must be written in Simplified Chinese (简体中文)."
    return "Output language requirement: All natural-language fields must be written in English."


def _pick_primary_actor(actor_ontology: dict[str, Any]) -> dict[str, Any]:
    actors = actor_ontology.get("actors") or []
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        actor_type = str(actor.get("type") or "").strip().lower()
        if actor_type == "strategicactor":
            return actor
    for actor in actors:
        if isinstance(actor, dict):
            return actor
    return {}


def _events_for_actor(actor_ontology: dict[str, Any], actor_id: str) -> list[dict[str, Any]]:
    events = actor_ontology.get("events") or []
    if not isinstance(events, list):
        return []

    matched: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        involved = {str(item).strip() for item in (event.get("actors_involved") or []) if str(item).strip()}
        if actor_id and actor_id in involved:
            matched.append(event)
    matched.sort(key=lambda item: str(item.get("date") or item.get("time") or ""))
    return matched


def _extract_json_object(text: str) -> dict[str, Any]:
    def _try_decode(candidate: str) -> dict[str, Any]:
        decoder = json.JSONDecoder()
        start = candidate.find("{")
        if start == -1:
            raise ValueError("LLM response does not contain a JSON object")
        payload, _ = decoder.raw_decode(candidate[start:])
        if not isinstance(payload, dict):
            raise ValueError("LLM response JSON payload is not an object")
        return payload

    def _sanitize(candidate: str) -> str:
        cleaned = str(candidate or "").replace("\ufeff", "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = re.sub(r"```(?:json)?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"(^|\s)//.*?$", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
        return cleaned.strip()

    raw = str(text or "")
    candidates: list[str] = [raw]

    fenced = re.findall(r"```(?:json)?\s*(.*?)\s*```", raw, flags=re.IGNORECASE | re.DOTALL)
    candidates.extend(fenced)

    errors: list[str] = []
    for candidate in candidates:
        try:
            return _try_decode(candidate)
        except Exception as exc:
            errors.append(exc.__class__.__name__)

        try:
            return _try_decode(_sanitize(candidate))
        except Exception as exc:
            errors.append(exc.__class__.__name__)

        try:
            loaded = yaml.safe_load(_sanitize(candidate))
            if isinstance(loaded, dict):
                return loaded
            errors.append("YAMLSafeLoadNotObject")
        except Exception as exc:
            errors.append(exc.__class__.__name__)

    raise ValueError(f"Unable to parse JSON object from LLM response ({'/'.join(errors[-4:])})")


def _invoke_json_prompt(llm_client: Any, prompt: str) -> dict[str, Any]:
    response = llm_client.invoke(prompt)
    content = response.content if isinstance(response.content, str) else json.dumps(response.content)
    try:
        return _extract_json_object(content)
    except Exception:
        retry_prompt = build_json_retry_prompt(prompt)
        retry_response = llm_client.invoke(retry_prompt)
        retry_content = retry_response.content if isinstance(retry_response.content, str) else json.dumps(retry_response.content)
        return _extract_json_object(retry_content)


def _normalize_traits(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    traits: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        trait = str(item.get("trait") or item.get("name") or "").strip()
        evidence_summary = str(item.get("evidence_summary") or item.get("evidence") or "").strip()
        if trait and evidence_summary:
            traits.append({"trait": trait, "evidence_summary": evidence_summary})
    return traits


def _build_persona_prompt(
    *,
    actor_name: str,
    profile: dict[str, Any],
    events: list[dict[str, Any]],
    output_language: str,
) -> str:
    base_prompt = build_persona_insight_prompt().format(
        actor_name=actor_name,
        background_facts=json.dumps(profile.get("background_facts") or {}, ensure_ascii=False),
        strategic_style=json.dumps(profile.get("strategic_style") or {}, ensure_ascii=False),
    )

    prompt = (
        base_prompt
        + "\n"
        + _language_instruction(output_language)
        + "\n\nReturn JSON object only with keys: persona_insight.narrative, persona_insight.key_traits, persona_insight.consistency_score."
        + "\nkey_traits must be an array of objects with trait and evidence_summary."
        + "\nconsistency_score must be a number in [0,1]."
    )

    if output_language == "zh":
        prompt += "\n叙事要求：narrative 必须是 200-300 字，叙事风格，清楚说明背景、决策风格与关键事件的内在动力。"
    else:
        prompt += "\nNarrative requirement: 180-260 words, narrative style, clearly connecting background, decision style, and major events."

    event_view = [
        {
            "id": str(item.get("id") or "").strip(),
            "name": str(item.get("name") or item.get("event") or "").strip(),
            "date": str(item.get("date") or item.get("time") or "").strip(),
            "description": str(item.get("description") or "").strip(),
        }
        for item in events[:10]
    ]
    prompt += "\n\nRelated strategic events (JSON):\n" + json.dumps(event_view, ensure_ascii=False)
    return prompt


def generate_persona_insight(
    *,
    case_id: str,
    actor_ontology: dict[str, Any],
    strategy_ontology: dict[str, Any] | None = None,
    llm_client: Any = None,
    config_path: str | None = None,
    output_language: str = "en",
) -> dict[str, Any]:
    del strategy_ontology

    actor = _pick_primary_actor(actor_ontology)
    actor_name = str(actor.get("name") or "Strategic Actor").strip() or "Strategic Actor"
    actor_id = str(actor.get("id") or "").strip()
    profile = actor.get("profile") or {}
    events = _events_for_actor(actor_ontology, actor_id)

    runtime_client = llm_client
    if runtime_client is None:
        config = load_llm_config(config_path or "config/llm.toml")
        runtime_client = create_chat_client(config)

    language = _normalize_output_language(output_language)
    prompt = _build_persona_prompt(
      actor_name=actor_name,
      profile=profile,
      events=events,
      output_language=language,
    )
    payload = _invoke_json_prompt(runtime_client, prompt)

    insight = payload.get("persona_insight") if isinstance(payload.get("persona_insight"), dict) else payload
    if not isinstance(insight, dict):
        raise ValueError("persona_insight payload must be a JSON object")

    narrative = str(insight.get("narrative") or "").strip()
    traits = _normalize_traits(insight.get("key_traits"))
    score_raw = insight.get("consistency_score") or 0
    try:
        consistency_score = float(score_raw)
    except Exception:
        consistency_score = 0.85
    consistency_score = max(0.0, min(1.0, consistency_score))

    return {
        "query": {"type": "persona", "case_id": case_id},
        "run_meta": {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt_version": get_analyze_prompt_version_token("persona"),
            "mode": "skeleton-deterministic",
        },
        "persona_insight": {
            "narrative": narrative,
            "key_traits": traits,
            "consistency_score": consistency_score,
        },
    }


def generate_and_save_persona_insight(
    *,
    case_id: str,
    actor_ontology: dict[str, Any],
    strategy_ontology: dict[str, Any] | None,
    config_path: str,
    output_path: str | Path,
    output_language: str = "en",
) -> Path:
    payload = generate_persona_insight(
        case_id=case_id,
        actor_ontology=actor_ontology,
        strategy_ontology=strategy_ontology,
        config_path=config_path,
        output_language=output_language,
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved analyze persona payload to {path}")
    return path


def map_major_conclusions_to_evidence(
    conclusions: list[dict[str, Any]],
    evidence_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {
        str(item.get("evidence_id") or item.get("id") or "").strip(): item
        for item in evidence_records
        if isinstance(item, dict)
    }
    mapped: list[dict[str, Any]] = []
    for conclusion in conclusions:
        if not isinstance(conclusion, dict):
            continue
        refs = [str(ref).strip() for ref in (conclusion.get("evidence_refs") or []) if str(ref).strip()]
        mapped.append(
            {
                "conclusion": str(conclusion.get("text") or conclusion.get("summary") or "").strip(),
                "evidence_refs": refs,
                "evidence_items": [by_id[ref] for ref in refs if ref in by_id],
            }
        )
    return mapped


def apply_contradiction_confidence_flag(
    evidence_records: list[dict[str, Any]],
) -> str:
    groups: dict[str, int] = {}
    for record in evidence_records:
        if not isinstance(record, dict):
            continue
        group = str(record.get("contradiction_group") or "").strip()
        if not group:
            continue
        groups[group] = groups.get(group, 0) + 1
    has_conflict = any(count > 1 for count in groups.values())
    return "reduced-confidence" if has_conflict else "full-confidence"


