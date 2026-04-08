"""Replay persistence and counterfactual comparison utilities."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from omen.explain.report import build_explanation_report
from omen.ingest.validators.scenario import ScenarioConfig, validate_scenario_or_raise
from omen.simulation.condition_types import normalize_semantic_conditions
from omen.simulation.engine import run_simulation
from omen.simulation.precision_metrics import (
    evaluate_directional_correctness,
    evaluate_trace_completeness,
)


def save_run_result(result: dict[str, Any], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def load_run_result(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _apply_override(payload: dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cursor: Any = payload
    for part in parts[:-1]:
        if isinstance(cursor, list):
            cursor = cursor[int(part)]
        else:
            cursor = cursor[part]
    final = parts[-1]
    if isinstance(cursor, list):
        cursor[int(final)] = value
    else:
        cursor[final] = value


def create_counterfactual_config(
    config: ScenarioConfig,
    overrides: dict[str, Any],
) -> ScenarioConfig:
    payload = deepcopy(config.model_dump(mode="python"))
    for key, value in overrides.items():
        _apply_override(payload, key, value)
    return validate_scenario_or_raise(payload)


def run_counterfactual(
    baseline_config: ScenarioConfig,
    overrides: dict[str, Any],
    ontology_setup: dict[str, Any] | None = None,
) -> tuple[ScenarioConfig, dict[str, Any]]:
    variation = create_counterfactual_config(baseline_config, overrides)
    return variation, run_simulation(variation, ontology_setup=ontology_setup)


def _parse_failure_activation_rules(result: dict[str, Any]) -> list[dict[str, Any]]:
    ontology_setup = result.get("ontology_setup", {}) or {}
    applied_axioms = ontology_setup.get("applied_axioms", {}) or {}
    counterfactual_rules = list(applied_axioms.get("counterfactual") or [])

    rules: list[dict[str, Any]] = []
    for rule_id in counterfactual_rules:
        rules.append(
            {
                "rule_id": str(rule_id),
                "rule_type": "failure_activation",
                "trigger": {
                    "metric": "adoption_resistance",
                    "operator": ">=",
                    "threshold": 0.7,
                },
                "min_steps": 6,
            }
        )
    return rules


def _evaluate_failure_activation(
    variation_result: dict[str, Any],
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    ontology_setup = variation_result.get("ontology_setup", {}) or {}
    adoption_resistance = (
        ((ontology_setup.get("space_summary") or {}).get("adoption_resistance"))
        if isinstance(ontology_setup, dict)
        else None
    )

    evaluations: list[dict[str, Any]] = []
    for rule in rules:
        trigger = rule.get("trigger", {})
        threshold = trigger.get("threshold")
        try:
            threshold_value = float(threshold)
        except (TypeError, ValueError):
            threshold_value = 0.7

        triggered = isinstance(adoption_resistance, (int, float)) and adoption_resistance >= threshold_value
        evaluations.append(
            {
                "rule_id": rule.get("rule_id"),
                "triggered": triggered,
                "observation": {
                    "adoption_resistance": adoption_resistance,
                    "threshold": threshold_value,
                },
            }
        )

    return {
        "rules": rules,
        "evaluations": evaluations,
        "triggered": any(item.get("triggered") for item in evaluations),
        "triggered_rule_ids": [
            str(item.get("rule_id")) for item in evaluations if item.get("triggered")
        ],
    }


def compare_run_results(
    baseline_result: dict[str, Any],
    variation_result: dict[str, Any],
    conditions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    baseline_edges = len(baseline_result.get("final_competition_edges", []))
    variation_edges = len(variation_result.get("final_competition_edges", []))
    baseline_winner_edges = baseline_result.get("winner", {}).get("user_edge_count", 0)
    variation_winner_edges = variation_result.get("winner", {}).get("user_edge_count", 0)
    deltas = [
        {
            "metric": "winner_user_edge_count",
            "baseline": baseline_winner_edges,
            "variation": variation_winner_edges,
            "delta": variation_winner_edges - baseline_winner_edges,
        },
        {
            "metric": "competition_edge_count",
            "baseline": baseline_edges,
            "variation": variation_edges,
            "delta": variation_edges - baseline_edges,
        },
        {
            "metric": "snapshot_count",
            "baseline": len(baseline_result.get("snapshots", [])),
            "variation": len(variation_result.get("snapshots", [])),
            "delta": len(variation_result.get("snapshots", []))
            - len(baseline_result.get("snapshots", [])),
        },
    ]
    semantic_conditions = normalize_semantic_conditions(conditions or [])
    failure_rules = _parse_failure_activation_rules(variation_result)
    failure_activation = _evaluate_failure_activation(variation_result, failure_rules)
    comparison = {
        "baseline_run_id": baseline_result.get("run_id"),
        "variation_run_id": variation_result.get("run_id"),
        "baseline_outcome_class": baseline_result.get("outcome_class"),
        "variation_outcome_class": variation_result.get("outcome_class"),
        "winner_changed": baseline_result.get("winner", {}).get("actor_id")
        != variation_result.get("winner", {}).get("actor_id"),
        "conditions": semantic_conditions,
        "deltas": deltas,
        "failure_activation": failure_activation,
    }
    comparison["explanation"] = build_explanation_report(variation_result, comparison=comparison)
    directional = evaluate_directional_correctness(
        comparison,
        conditions=semantic_conditions,
    )
    trace = evaluate_trace_completeness(
        comparison["explanation"].get("outcome_evidence_links", [])
    )
    comparison["precision_summary"] = {
        "directional_correctness": directional,
        "trace_completeness": trace,
    }
    return comparison
