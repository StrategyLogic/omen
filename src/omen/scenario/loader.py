"""Artifact loader helpers for Spec 8 flow visualization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def discover_spec8_pack_candidates(
    data_root: str | Path = "data/scenarios",
    output_root: str | Path = "output",
) -> list[str]:
    data_base = Path(data_root)
    output_base = Path(output_root)
    ids: set[str] = set()

    if data_base.exists():
        for entry in data_base.iterdir():
            if entry.is_dir() and (entry / "situation.json").exists():
                ids.add(entry.name)

    if output_base.exists():
        for entry in output_base.iterdir():
            if entry.is_dir() and (entry / "result.json").exists():
                ids.add(entry.name)

    return sorted(ids)


def _find_output_pack_by_result_ref(output_root: Path, scenario_pack_ref: str) -> str | None:
    for entry in output_root.iterdir() if output_root.exists() else []:
        if not entry.is_dir():
            continue
        payload = _read_json(entry / "result.json")
        if not payload:
            continue
        if str(payload.get("scenario_pack_ref") or "").strip() == scenario_pack_ref:
            return entry.name
    return None


def load_spec8_flow_artifacts(
    *,
    pack_id: str,
    data_root: str | Path = "data/scenarios",
    output_root: str | Path = "output",
    output_pack_id: str | None = None,
) -> dict[str, Any]:
    data_base = Path(data_root)
    output_base = Path(output_root)
    data_pack = data_base / pack_id

    situation = _read_json(data_pack / "situation.json")
    scenario_pack = _read_json(data_pack / "scenario_pack.json")
    prior_snapshot = _read_json(data_pack / "traces" / "prior_snapshot.json")
    planning_query = _read_json(data_pack / "traces" / "planning_query.json")
    reason_chain = _read_json(data_pack / "traces" / "reason_chain.json")

    resolved_output_pack = output_pack_id or pack_id
    result = _read_json(output_base / resolved_output_pack / "result.json")
    explanation = _read_json(output_base / resolved_output_pack / "explanation.json")

    scenario_pack_ref = str((result or {}).get("scenario_pack_ref") or "").strip()
    if (result is None or explanation is None) and not output_pack_id and scenario_pack_ref != pack_id:
        # If result exists but references another pack id, trust explicit user output directory.
        pass
    if result is None and not output_pack_id:
        inferred = _find_output_pack_by_result_ref(output_base, pack_id)
        if inferred:
            resolved_output_pack = inferred
            result = _read_json(output_base / resolved_output_pack / "result.json")
            explanation = _read_json(output_base / resolved_output_pack / "explanation.json")

    actor_profile_payload: dict[str, Any] | None = None
    actor_profile_ref = str((situation or {}).get("context", {}).get("actor_ref") or "").strip()
    if actor_profile_ref:
        actor_path = Path(actor_profile_ref)
        if not actor_path.is_absolute():
            actor_path = Path.cwd() / actor_path
        actor_profile_payload = _read_json(actor_path)

    return {
        "pack_id": pack_id,
        "output_pack_id": resolved_output_pack,
        "paths": {
            "situation": str(data_pack / "situation.json"),
            "situation_md": str(data_pack / "situation.md"),
            "scenario_pack": str(data_pack / "scenario_pack.json"),
            "prior_snapshot": str(data_pack / "traces" / "prior_snapshot.json"),
            "planning_query": str(data_pack / "traces" / "planning_query.json"),
            "reason_chain": str(data_pack / "traces" / "reason_chain.json"),
            "result": str(output_base / resolved_output_pack / "result.json"),
            "explanation": str(output_base / resolved_output_pack / "explanation.json"),
            "actor_profile": actor_profile_ref,
        },
        "payloads": {
            "situation": situation,
            "scenario_pack": scenario_pack,
            "prior_snapshot": prior_snapshot,
            "planning_query": planning_query,
            "reason_chain": reason_chain,
            "result": result,
            "explanation": explanation,
            "actor_profile": actor_profile_payload,
        },
    }