"""Build condition→rule→evidence links for outcome deltas."""

from __future__ import annotations

from typing import Any


def build_outcome_evidence_links(
    result: dict[str, Any],
    comparison: dict[str, Any] | None,
    *,
    rule_trace_references: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if not comparison:
        return []

    conditions = comparison.get("conditions", [])
    deltas = comparison.get("deltas", [])
    applied_axioms = (result.get("ontology_setup") or {}).get("applied_axioms", {})

    rule_ids = [str(ref.get("rule_id")) for ref in (rule_trace_references or []) if ref.get("rule_id")]
    evidence_refs = [str(k) for k in applied_axioms.keys()]
    condition_refs = [
        str(condition.get("description") or condition.get("semantic_type") or condition.get("type") or "condition")
        for condition in conditions
    ]

    links: list[dict[str, Any]] = []
    for idx, delta in enumerate(deltas):
        metric = str(delta.get("metric", f"metric_{idx}"))
        trace_components = 0
        if condition_refs:
            trace_components += 1
        if rule_ids:
            trace_components += 1
        if evidence_refs:
            trace_components += 1

        links.append(
            {
                "link_id": f"{result.get('run_id', 'run')}-{idx}",
                "outcome_delta_id": metric,
                "condition_refs": condition_refs,
                "rule_chain_refs": rule_ids,
                "evidence_refs": evidence_refs,
                "trace_completeness": trace_components / 3.0,
            }
        )

    return links
