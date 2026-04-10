"""Situation artifact validation helpers."""

from __future__ import annotations

from pathlib import Path

from omen.ingest.models import SituationArtifactModel
from omen.scenario.ingest_validator import IncompleteDeterministicPackError
from omen.scenario.ingest_validator import DeferredScopeFeatureError


_DEFERRED_DYNAMIC_MARKERS = {
    "dynamic_authoring",
    "dynamic_scenarios",
    "free_form_scenarios",
    "scenario_generator",
}

_DEFERRED_ENTERPRISE_MARKERS = {
    "enterprise_resistance_extensions",
    "enterprise_template_catalog",
    "resistance_extension_profiles",
    "custom_resistance_dimensions",
    "enterprise_resistance_profile",
}


def validate_situation_source_or_raise(situation_file: str | Path) -> None:
    text = Path(situation_file).read_text(encoding="utf-8")
    lowered = text.lower()

    for marker in _DEFERRED_DYNAMIC_MARKERS:
        if marker in lowered:
            raise DeferredScopeFeatureError(
                f"`{marker}` is deferred scope in this release. "
                "Only deterministic A/B/C scenario packs are supported."
            )

    for marker in _DEFERRED_ENTERPRISE_MARKERS:
        if marker in lowered:
            raise DeferredScopeFeatureError(
                f"`{marker}` is deferred scope. Enterprise resistance extensions are not supported in this release."
            )


def validate_situation_artifact_or_raise(payload: dict) -> SituationArtifactModel:
    artifact = SituationArtifactModel.model_validate(payload)
    if artifact.version != "0.1.0":
        raise IncompleteDeterministicPackError(
            f"situation artifact version must be 0.1.0, got {artifact.version!r}"
        )
    if not artifact.signals:
        raise IncompleteDeterministicPackError("situation artifact missing signals")
    required_signal_fields = (
        "id",
        "name",
        "domain",
        "strength",
        "direction",
        "mapped_targets",
        "cascade_rules",
        "market_constraints",
        "mechanism_note",
    )
    allowed_domains = {"tech", "market", "capital", "standard", "policy"}
    allowed_impact_types = {"driver", "constraint", "amplifier", "dampener"}
    allowed_directions = {"up", "down", "mixed"}
    allowed_lags = {"short", "medium", "long"}
    required_conditions_by_type = {
        "driver": ("activation_condition", "expected_effect"),
        "constraint": ("binding_condition", "release_condition", "expected_effect"),
        "amplifier": ("modulation_target", "modulation_condition", "modulation_factor", "expected_effect"),
        "dampener": ("modulation_target", "modulation_condition", "modulation_factor", "expected_effect"),
    }

    for index, signal in enumerate(artifact.signals, start=1):
        for field in required_signal_fields:
            if field not in signal:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} missing required field `{field}`"
                )
            value = signal.get(field)
            if value is None or value == "":
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} missing required field `{field}`"
                )

        domain = str(signal.get("domain") or "").strip()
        if domain not in allowed_domains:
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} has invalid domain {domain!r}"
            )

        strength = signal.get("strength")
        if not isinstance(strength, (int, float)):
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} strength must be numeric in [0,1]"
            )
        if float(strength) < 0.0 or float(strength) > 1.0:
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} strength must be in [0,1]"
            )

        direction = str(signal.get("direction") or "").strip()
        if direction not in allowed_directions:
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} has invalid direction {direction!r}"
            )

        mapped_targets = signal.get("mapped_targets")
        if not isinstance(mapped_targets, list) or not mapped_targets:
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} mapped_targets must be a non-empty list"
            )
        for target_index, target in enumerate(mapped_targets, start=1):
            if not isinstance(target, dict):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} must be an object"
                )
            space = str(target.get("space") or "").strip()
            if space not in {"TechSpace", "MarketSpace"}:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} has invalid space {space!r}"
                )
            element_key = str(target.get("element_key") or "").strip()
            if not element_key:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} missing `element_key`"
                )
            impact_type = str(target.get("impact_type") or "").strip()
            if impact_type not in allowed_impact_types:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} has invalid impact_type {impact_type!r}"
                )
            impact_strength = target.get("impact_strength")
            if not isinstance(impact_strength, (int, float)):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} impact_strength must be numeric in [0,1]"
                )
            if float(impact_strength) < 0.0 or float(impact_strength) > 1.0:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} impact_strength must be in [0,1]"
                )

            mechanism_conditions = target.get("mechanism_conditions")
            if not isinstance(mechanism_conditions, dict):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} mechanism_conditions must be an object"
                )

            for field in required_conditions_by_type[impact_type]:
                value = mechanism_conditions.get(field)
                if field == "modulation_factor":
                    if not isinstance(value, (int, float)) or float(value) < 0.0 or float(value) > 1.0:
                        raise IncompleteDeterministicPackError(
                            f"situation signal #{index} mapped_target #{target_index} `{field}` must be numeric in [0,1]"
                        )
                    continue

                text = str(value or "").strip()
                if not text:
                    raise IncompleteDeterministicPackError(
                        f"situation signal #{index} mapped_target #{target_index} missing `{field}`"
                    )

        cascade_rules = signal.get("cascade_rules")
        if not isinstance(cascade_rules, list):
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} field `cascade_rules` must be a list"
            )
        if not cascade_rules:
            no_cascade_reason = str(signal.get("no_cascade_reason") or "").strip()
            if not no_cascade_reason:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} must include cascade_rules or no_cascade_reason"
                )
        for cascade_index, cascade in enumerate(cascade_rules, start=1):
            if not isinstance(cascade, dict):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} cascade_rule #{cascade_index} must be an object"
                )
            trigger = str(cascade.get("trigger_condition") or "").strip()
            next_signal_id = str(cascade.get("next_signal_id") or "").strip()
            expected_lag = str(cascade.get("expected_lag") or "").strip()
            if not trigger or not next_signal_id:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} cascade_rule #{cascade_index} missing trigger_condition or next_signal_id"
                )
            if expected_lag not in allowed_lags:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} cascade_rule #{cascade_index} has invalid expected_lag {expected_lag!r}"
                )

        market_constraints = signal.get("market_constraints")
        if not isinstance(market_constraints, list) or not market_constraints:
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} field `market_constraints` must be a non-empty list"
            )
        for constraint_index, constraint in enumerate(market_constraints, start=1):
            if not isinstance(constraint, dict):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} market_constraint #{constraint_index} must be an object"
                )
            constraint_key = str(constraint.get("constraint_key") or "").strip()
            binding_strength = constraint.get("binding_strength")
            if not constraint_key:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} market_constraint #{constraint_index} missing `constraint_key`"
                )
            if not isinstance(binding_strength, (int, float)):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} market_constraint #{constraint_index} binding_strength must be numeric in [0,1]"
                )
            if float(binding_strength) < 0.0 or float(binding_strength) > 1.0:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} market_constraint #{constraint_index} binding_strength must be in [0,1]"
                )

    return artifact
