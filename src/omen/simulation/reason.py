"""Reason-chain and simulate-layer helpers."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
import re
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - fallback for minimal environments
    class _YamlFallback:
        @staticmethod
        def safe_load(_: str) -> Any:
            raise ValueError("yaml parser unavailable")

    yaml = _YamlFallback()  # type: ignore[assignment]

REASONING_ORDER: tuple[str, ...] = (
    "seed",
    "constraint_activation",
    "target_or_objective",
    "gap",
    "required_or_warning_or_blocking",
)


def build_hierarchical_step_id(major: int, minor: int) -> str:
    if major < 1 or minor < 1:
        raise ValueError("step id major/minor must be >= 1")
    return f"step_{major}.{minor}"


def is_hierarchical_step_id(step_id: str) -> bool:
    return bool(str(step_id or "").strip())


def validate_reason_chain_step_ids(steps: list[dict[str, Any]]) -> bool:
    if not isinstance(steps, list) or not steps:
        return False
    return all(is_hierarchical_step_id(str(item.get("step_id") or "")) for item in steps)


def reasoning_order_is_valid(step_types: list[str]) -> bool:
    order_index = {name: idx for idx, name in enumerate(REASONING_ORDER)}
    last = -1
    for raw in step_types:
        name = str(raw or "").strip()
        if name not in order_index:
            continue
        current = order_index[name]
        if current < last:
            return False
        last = current
    return True


def blocking_has_activation_links(blocking_item: dict[str, Any]) -> bool:
    if not isinstance(blocking_item, dict):
        return False
    activation_refs = [str(item).strip() for item in (blocking_item.get("activation_step_ids") or []) if str(item).strip()]
    reason_refs = [str(item).strip() for item in (blocking_item.get("reason_step_ids") or []) if str(item).strip()]
    return bool(activation_refs and reason_refs)


def extract_conclusion_buckets(conclusions: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    raw = dict(conclusions or {})
    source = dict(raw.get("scenario_conditions") or raw)

    def _normalize_items(items: list[Any], *, bucket: str) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, str):
                text = item.strip()
                if not text:
                    continue
                row: dict[str, Any] = {"text": text, "reason_step_ids": []}
                if bucket == "blocking":
                    row["activation_step_ids"] = []
                normalized.append(row)
                continue
            if isinstance(item, dict):
                text = str(item.get("text") or item.get("summary") or "").strip()
                if not text:
                    continue
                row = {
                    "text": text,
                    "reason_step_ids": [
                        str(x).strip()
                        for x in (item.get("reason_step_ids") or [])
                        if str(x).strip()
                    ],
                }
                if bucket == "blocking":
                    row["activation_step_ids"] = [
                        str(x).strip()
                        for x in (item.get("activation_step_ids") or [])
                        if str(x).strip()
                    ]
                normalized.append(row)
        return normalized

    return {
        "required": _normalize_items(list(source.get("required") or []), bucket="required"),
        "warning": _normalize_items(list(source.get("warning") or []), bucket="warning"),
        "blocking": _normalize_items(list(source.get("blocking") or []), bucket="blocking"),
    }


def build_linked_evidence_refs(reason_chain: dict[str, Any]) -> list[dict[str, Any]]:
    conclusions = extract_conclusion_buckets(dict(reason_chain.get("conclusions") or {}))
    steps = [item for item in (reason_chain.get("steps") or []) if isinstance(item, dict)]
    default_reason_step_ids = [
        str(item.get("step_id") or "").strip()
        for item in steps
        if str(item.get("step_type") or "").strip()
        in {"required_or_warning_or_blocking", "strategic_conditions"}
        and str(item.get("step_id") or "").strip()
    ]
    default_activation_step_ids = [
        str(item.get("step_id") or "").strip()
        for item in steps
        if str(item.get("step_type") or "").strip() == "constraint_activation"
        and str(item.get("step_id") or "").strip()
    ]

    if not default_reason_step_ids:
        fallback = str(steps[-1].get("step_id") or "").strip() if steps else ""
        if fallback:
            default_reason_step_ids = [fallback]

    refs: list[dict[str, Any]] = []
    for bucket in ("required", "warning", "blocking"):
        for index, item in enumerate(list(conclusions.get(bucket) or []), start=1):
            if not isinstance(item, dict):
                continue
            reason_ids = [str(x).strip() for x in (item.get("reason_step_ids") or []) if str(x).strip()]
            activation_ids = [str(x).strip() for x in (item.get("activation_step_ids") or []) if str(x).strip()]
            if not reason_ids:
                reason_ids = list(default_reason_step_ids)
            if bucket == "blocking" and not activation_ids:
                activation_ids = list(default_activation_step_ids)
            refs.append(
                {
                    "evidence_id": f"{bucket}_{index}",
                    "bucket": bucket,
                    "summary": str(item.get("text") or "").strip(),
                    "reason_step_ids": reason_ids,
                    "activation_step_ids": activation_ids,
                }
            )
    return refs


def build_reason_chain_artifact(
    *,
    run_id: str,
    scenario_pack_ref: str,
    scenario_chains: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "reason_chain",
        "version": "reason_chain_v1",
        "run_id": run_id,
        "scenario_pack_ref": scenario_pack_ref,
        "scenario_chains": scenario_chains,
    }


def build_reason_chain_view_model_artifact(
    *,
    run_id: str,
    scenario_pack_ref: str,
    scenario_chains: list[dict[str, Any]],
) -> dict[str, Any]:
    graph_nodes: list[dict[str, Any]] = []
    graph_edges: list[dict[str, Any]] = []
    for row in scenario_chains:
        scenario_key = str(row.get("scenario_key") or "")
        reason_chain = dict(row.get("reason_chain") or {})
        steps = list(reason_chain.get("steps") or [])
        ordered_step_node_ids: list[str] = []
        for step in steps:
            step_id = str(step.get("step_id") or "").strip()
            node_id = f"{scenario_key}:{step_id}"
            ordered_step_node_ids.append(node_id)
            graph_nodes.append(
                {
                    "id": node_id,
                    "scenario_key": scenario_key,
                    "node_type": "reason_step",
                    "step_id": step_id,
                    "step_type": str(step.get("step_type") or ""),
                    "label": str(step.get("summary") or ""),
                }
            )

        for index in range(1, len(ordered_step_node_ids)):
            graph_edges.append(
                {
                    "from": ordered_step_node_ids[index - 1],
                    "to": ordered_step_node_ids[index],
                    "edge_type": "next",
                }
            )

        conclusions = dict(reason_chain.get("conclusions") or {})
        for bucket in ("required", "warning", "blocking"):
            for index, item in enumerate(list(conclusions.get(bucket) or []), start=1):
                if not isinstance(item, dict):
                    continue
                claim_id = f"{scenario_key}:claim:{bucket}:{index}"
                graph_nodes.append(
                    {
                        "id": claim_id,
                        "scenario_key": scenario_key,
                        "node_type": "claim",
                        "bucket": bucket,
                        "label": str(item.get("text") or ""),
                    }
                )
                for reason_step_id in list(item.get("reason_step_ids") or []):
                    rid = str(reason_step_id).strip()
                    if rid:
                        graph_edges.append(
                            {
                                "from": f"{scenario_key}:{rid}",
                                "to": claim_id,
                                "edge_type": "supports",
                            }
                        )
                for activation_step_id in list(item.get("activation_step_ids") or []):
                    aid = str(activation_step_id).strip()
                    if aid:
                        graph_edges.append(
                            {
                                "from": f"{scenario_key}:{aid}",
                                "to": claim_id,
                                "edge_type": "activates",
                            }
                        )

    return {
        "artifact_type": "reason_chain_view_model",
        "version": "reason_chain_view_model_v1",
        "run_id": run_id,
        "scenario_pack_ref": scenario_pack_ref,
        "graph": {
            "nodes": graph_nodes,
            "edges": graph_edges,
        },
    }


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


def render_scenario_reason_chain_prompt(
    *,
    scenario_json: dict[str, Any],
    actor_profile_json: dict[str, Any],
    planning_query_json: dict[str, Any],
    situation_markdown: str,
    scenario_key: str,
) -> str:
    from omen.ingest.synthesizer.clients import render_prompt_template
    from omen.ingest.synthesizer.prompts.registry import get_prompt_template

    template = get_prompt_template("scenario_reason_chain_prompt", tier="base")
    return render_prompt_template(
        template,
        {
            "scenario_json": json.dumps(scenario_json, ensure_ascii=False),
            "scenario_key": str(scenario_key or ""),
            "actor_profile_json": json.dumps(actor_profile_json, ensure_ascii=False),
            "planning_query_json": json.dumps(planning_query_json, ensure_ascii=False),
            "situation_markdown": str(situation_markdown or ""),
        },
    )


def try_generate_scenario_reason_chain_via_llm(
    *,
    scenario_json: dict[str, Any],
    actor_profile_json: dict[str, Any],
    planning_query_json: dict[str, Any],
    situation_markdown: str,
    config_path: str | None = None,
    debug_output_path: str | None = None,
    scenario_key: str | None = None,
) -> dict[str, Any] | None:
    from omen.ingest.synthesizer.clients import invoke_text_prompt
    from omen.ingest.synthesizer.prompts import build_json_retry_prompt

    def _append_debug(
        *,
        status: str,
        prompt_text: str,
        raw_response: str,
        parsed_payload: dict[str, Any] | None,
    ) -> None:
        if not debug_output_path:
            return
        try:
            path = Path(debug_output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            payload_text = json.dumps(parsed_payload, ensure_ascii=False, indent=2) if isinstance(parsed_payload, dict) else "null"
            entry = (
                "\n"
                "===== scenario_reason_chain_llm_debug =====\n"
                f"timestamp: {datetime.datetime.now().isoformat()}\n"
                f"scenario_key: {str(scenario_key or '')}\n"
                f"status: {status}\n"
                "--- prompt ---\n"
                f"{prompt_text}\n"
                "--- raw_response ---\n"
                f"{raw_response}\n"
                "--- parsed_payload ---\n"
                f"{payload_text}\n"
            )
            with path.open("a", encoding="utf-8") as handle:
                handle.write(entry)
        except Exception:
            return

    prompt = render_scenario_reason_chain_prompt(
        scenario_json=scenario_json,
        scenario_key=str(scenario_key or scenario_json.get("scenario_key") or ""),
        actor_profile_json=actor_profile_json,
        planning_query_json=planning_query_json,
        situation_markdown=situation_markdown,
    )
    try:
        content = invoke_text_prompt(config_path=config_path, user_prompt=prompt)
        payload = _extract_json_object(content)
        _append_debug(
            status="ok",
            prompt_text=prompt,
            raw_response=content,
            parsed_payload=payload if isinstance(payload, dict) else None,
        )
        return payload if isinstance(payload, dict) else None
    except Exception as exc:
        retry_payload: dict[str, Any] | None = None
        retry_raw = ""
        try:
            retry_prompt = build_json_retry_prompt(prompt)
            retry_raw = invoke_text_prompt(config_path=config_path, user_prompt=retry_prompt)
            parsed_retry = _extract_json_object(retry_raw)
            retry_payload = parsed_retry if isinstance(parsed_retry, dict) else None
        except Exception:
            retry_payload = None

        _append_debug(
            status=(
                "ok_after_retry"
                if isinstance(retry_payload, dict)
                else f"parse_or_invoke_error:{exc.__class__.__name__}"
            ),
            prompt_text=prompt,
            raw_response=(
                f"{content if isinstance(locals().get('content'), str) else ''}"
                + ("\n\n--- retry_raw_response ---\n" + retry_raw if retry_raw else "")
            ),
            parsed_payload=retry_payload,
        )
        return retry_payload


def _normalize_llm_reason_chain(llm_chain: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(llm_chain, dict):
        return None
    steps = list(llm_chain.get("steps") or [])
    if not steps:
        return None

    normalized_steps: list[dict[str, Any]] = []
    for index, raw in enumerate(steps, start=1):
        if not isinstance(raw, dict):
            continue
        step_id = str(raw.get("step_id") or "").strip() or f"step_{index}"
        step_type = str(raw.get("step_type") or "unknown").strip() or "unknown"
        summary = str(raw.get("summary") or raw.get("description") or step_type).strip() or step_type
        input_refs = list(raw.get("input_refs") or raw.get("inputs") or [])
        normalized_steps.append(
            {
                **raw,
                "step_id": step_id,
                "step_type": step_type,
                "summary": summary,
                "input_refs": input_refs,
            }
        )

    if not normalized_steps:
        return None

    normalized_conclusions = dict(llm_chain.get("conclusions") or {})
    if not normalized_conclusions:
        normalized_conclusions = {
            "required": [],
            "warning": [],
            "blocking": [],
        }

    return {
        "steps": normalized_steps,
        "intermediate": dict(llm_chain.get("intermediate") or {}),
        "conclusions": normalized_conclusions,
    }


def resolve_reason_chain_with_llm(
    *,
    scenario_key: str,
    scenario_ontology: dict[str, Any],
    scenario_result: dict[str, Any],
    actor_profile_ref: str,
    debug_output_path: str | None,
) -> tuple[dict[str, Any], str]:
    llm_scenario_input = {
        "scenario_key": scenario_key,
        "title": scenario_ontology.get("title"),
        "goal": scenario_ontology.get("goal"),
        "target": scenario_ontology.get("target"),
        "objective": scenario_ontology.get("objective"),
        "variables": list(scenario_ontology.get("variables") or []),
        "constraints": list(scenario_ontology.get("constraints") or []),
        "tradeoff_pressure": list(scenario_ontology.get("tradeoff_pressure") or []),
        "resistance_assumptions": dict(scenario_ontology.get("resistance_assumptions") or {}),
    }
    llm_payload = try_generate_scenario_reason_chain_via_llm(
        scenario_json=llm_scenario_input,
        actor_profile_json={
            "actor_profile_ref": actor_profile_ref,
            "actor_derivation": dict(scenario_result.get("actor_derivation") or {}),
            "selected_dimensions": list((scenario_result.get("selected_dimensions") or {}).get("selected_dimension_keys") or []),
            "resistance": dict(scenario_result.get("resistance") or {}),
        },
        planning_query_json={},
        situation_markdown="",
        debug_output_path=debug_output_path,
        scenario_key=scenario_key,
    )
    llm_chain = llm_payload.get("reason_chain") if isinstance(llm_payload, dict) and isinstance(llm_payload.get("reason_chain"), dict) else None
    normalized_llm = _normalize_llm_reason_chain(llm_chain or {})

    if normalized_llm is not None:
        return normalized_llm, "ok"
    raise ValueError(
        "LLM reason chain generation failed: response missing valid reason_chain payload "
        f"for scenario {scenario_key}"
    )


def build_recommendation_from_condition_sets(
    scenario_results: list[dict[str, Any]],
) -> str:
    if not scenario_results:
        return "No deterministic scenario result available."

    best = next(
        (
            item
            for item in scenario_results
            if not list((item.get("scenario_conditions") or {}).get("blocking") or [])
        ),
        scenario_results[0],
    )
    best_key = str(best.get("scenario_key") or "unknown")
    conditions = best.get("scenario_conditions") or {}
    blocking = list(conditions.get("blocking") or [])
    required = list(conditions.get("required") or [])

    if blocking:
        return (
            f"Scenario {best_key} has highest strategic potential but is currently blocked: "
            f"{'; '.join(blocking[:2])}."
        )

    required_hint = required[0] if required else "No required condition derived from reason_chain conclusions"
    return (
        f"Recommend scenario {best_key} as primary path. "
        f"First required condition: {required_hint}."
    )


def apply_partial_evidence_confidence_policy(
    *,
    evidence_refs: list[str],
    scenario_key: str | None = None,
) -> tuple[str, list[str]]:
    refs = [str(item).strip() for item in evidence_refs if str(item).strip()]
    if refs:
        return "full-confidence", []
    key = str(scenario_key or "unknown")
    return (
        "reduced-confidence",
        [f"Scenario {key}: no evidence refs linked in current iteration"],
    )


def link_blocking_to_reason_steps(
    blocking_texts: list[str],
    *,
    activation_step_id: str,
    reason_step_id: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for text in blocking_texts:
        normalized = str(text).strip()
        if not normalized:
            continue
        output.append(
            {
                "text": normalized,
                "activation_step_ids": [activation_step_id],
                "reason_step_ids": [reason_step_id],
            }
        )
    return output
