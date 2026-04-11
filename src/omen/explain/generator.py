"""Deterministic explanation generation from simulation result artifacts."""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import Any


def _parse_llm_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()

    def _try_decode(candidate: str) -> dict[str, Any]:
        start = str(candidate or "").find("{")
        if start == -1:
            raise ValueError("LLM response does not contain a JSON object")
        payload, _ = decoder.raw_decode(str(candidate)[start:])
        if not isinstance(payload, dict):
            raise ValueError("LLM response JSON payload is not an object")
        return payload

    def _sanitize(candidate: str) -> str:
        cleaned = str(candidate or "").replace("\ufeff", "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = re.sub(r"```(?:json)?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
        return cleaned.strip()

    raw = str(text or "")
    candidates = [raw]
    candidates.extend(re.findall(r"```(?:json)?\s*(.*?)\s*```", raw, flags=re.IGNORECASE | re.DOTALL))
    for candidate in candidates:
        try:
            return _try_decode(candidate)
        except Exception:
            pass
        try:
            return _try_decode(_sanitize(candidate))
        except Exception:
            pass
    raise ValueError("LLM response does not contain a parseable JSON object")


def normalize_action_suggestion_payload(payload: dict[str, Any]) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None
    source = payload
    nested = payload.get("action_suggestion")
    if isinstance(nested, dict):
        source = nested

    recommendation_summary = str(source.get("recommendation_summary") or "").strip()
    gap_summary = str(source.get("gap_summary") or "").strip()
    required_actions = str(source.get("required_actions") or "").strip()
    if not recommendation_summary or not gap_summary or not required_actions:
        return None

    return {
        "recommendation_summary": recommendation_summary,
        "gap_summary": gap_summary,
        "required_actions": required_actions,
    }


def _read_reason_chain_rows(result_payload: dict[str, Any], base_dir: Path) -> list[dict[str, Any]]:
    reason_chain_ref = str(result_payload.get("reason_chain_ref") or "").strip()
    if not reason_chain_ref:
        return []

    reason_chain_path = Path(reason_chain_ref)
    if not reason_chain_path.is_absolute():
        reason_chain_path = base_dir / reason_chain_path
    if not reason_chain_path.exists():
        return []

    reason_artifact = json.loads(reason_chain_path.read_text(encoding="utf-8"))
    return [
        row
        for row in list(reason_artifact.get("scenario_chains") or [])
        if isinstance(row, dict)
    ]


def _compact_scenario_results(scenario_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact_rows: list[dict[str, Any]] = []
    for row in scenario_results:
        conditions = dict(row.get("scenario_conditions") or {})
        compact_rows.append(
            {
                "scenario_key": str(row.get("scenario_key") or ""),
                "fit": str((row.get("capability_dilemma_fit") or {}).get("fit") or ""),
                "selected_dimensions": list((row.get("selected_dimensions") or {}).get("selected_dimension_keys") or []),
                "confidence_level": str(row.get("confidence_level") or ""),
                "required": [str(item).strip() for item in list(conditions.get("required") or []) if str(item).strip()],
                "warning": [str(item).strip() for item in list(conditions.get("warning") or []) if str(item).strip()],
                "blocking": [str(item).strip() for item in list(conditions.get("blocking") or []) if str(item).strip()],
                "evidence_count": len(list(row.get("evidence_refs") or [])),
            }
        )
    return compact_rows


def _compact_reason_chain_rows(reason_chain_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact_rows: list[dict[str, Any]] = []
    for row in reason_chain_rows:
        chain = dict(row.get("reason_chain") or {})
        steps = [item for item in list(chain.get("steps") or []) if isinstance(item, dict)]
        conclusions = dict(chain.get("conclusions") or {})
        blocking_items = [
            item
            for item in list(conclusions.get("blocking") or [])
            if isinstance(item, dict)
        ]
        compact_rows.append(
            {
                "scenario_key": str(row.get("scenario_key") or ""),
                "gap_step_summaries": [
                    str(item.get("summary") or "").strip()
                    for item in steps
                    if str(item.get("step_type") or "").strip() == "gap"
                    and str(item.get("summary") or "").strip()
                ],
                "blocking_activation_links": [
                    {
                        "text": str(item.get("text") or item.get("summary") or "").strip(),
                        "activation_step_ids": list(item.get("activation_step_ids") or []),
                        "reason_step_ids": list(item.get("reason_step_ids") or []),
                    }
                    for item in blocking_items
                ],
            }
        )
    return compact_rows


def _render_action_suggestion_prompt(
    *,
    scenario_pack_ref: str,
    actor_profile_ref: str,
    scenario_results: list[dict[str, Any]],
    reason_chains: list[dict[str, Any]],
) -> str:
    from omen.ingest.synthesizer.clients import render_prompt_template
    from omen.ingest.synthesizer.prompts.registry import get_prompt_template

    template = get_prompt_template("action_suggestion_prompt", tier="base")
    return render_prompt_template(
        template,
        {
            "scenario_pack_ref": str(scenario_pack_ref or ""),
            "actor_profile_ref": str(actor_profile_ref or ""),
            "scenario_results_json": json.dumps(_compact_scenario_results(scenario_results), ensure_ascii=False),
            "reason_chains_json": json.dumps(_compact_reason_chain_rows(reason_chains), ensure_ascii=False),
        },
    )


def generate_deterministic_explanation(
    *,
    result_payload: dict[str, Any],
    result_path: str | Path,
    debug: bool = False,
) -> dict[str, Any]:
    from omen.ingest.synthesizer.clients import invoke_text_prompt
    from omen.ingest.synthesizer.prompts import build_json_retry_prompt
    from omen.ingest.synthesizer.prompts.registry import get_action_suggestion_prompt_version_token

    base_dir = Path(result_path).resolve().parent
    scenario_pack_ref = str(result_payload.get("scenario_pack_ref") or "").strip()
    actor_profile_ref = str(result_payload.get("actor_profile_ref") or "").strip()
    scenario_results = [
        row
        for row in list(result_payload.get("scenario_results") or [])
        if isinstance(row, dict)
    ]
    reason_chain_rows = _read_reason_chain_rows(result_payload, base_dir)

    prompt = _render_action_suggestion_prompt(
        scenario_pack_ref=scenario_pack_ref,
        actor_profile_ref=actor_profile_ref,
        scenario_results=scenario_results,
        reason_chains=reason_chain_rows,
    )

    content = ""
    try:
        content = invoke_text_prompt(user_prompt=prompt)
        payload = _parse_llm_json_object(content)
    except Exception:
        retry_prompt = build_json_retry_prompt(prompt)
        retry_output = invoke_text_prompt(user_prompt=retry_prompt)
        payload = _parse_llm_json_object(retry_output)

    normalized = normalize_action_suggestion_payload(payload)
    if normalized is None:
        raise ValueError(
            "Explain generation failed: missing recommendation_summary/gap_summary/required_actions"
        )

    explanation = {
        "run_id": result_payload.get("run_id"),
        "scenario_pack_ref": scenario_pack_ref,
        "actor_profile_ref": actor_profile_ref,
        "reason_chain_ref": result_payload.get("reason_chain_ref"),
        "recommendation_summary": normalized["recommendation_summary"],
        "gap_summary": normalized["gap_summary"],
        "required_actions": normalized["required_actions"],
        "prompt_token": get_action_suggestion_prompt_version_token(),
        "generated_at": datetime.datetime.now().isoformat(),
    }

    if debug:
        debug_path = base_dir / "generation" / "output.txt"
        try:
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            entry = (
                "\n"
                "===== explain_action_suggestion_llm_debug =====\n"
                f"timestamp: {datetime.datetime.now().isoformat()}\n"
                "--- prompt (compact) ---\n"
                f"{prompt}\n"
                "--- parsed_payload ---\n"
                f"{json.dumps(explanation, ensure_ascii=False, indent=2)}\n"
            )
            with debug_path.open("a", encoding="utf-8") as handle:
                handle.write(entry)
        except Exception:
            pass

    return explanation
