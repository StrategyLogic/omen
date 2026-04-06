from omen.scenario.prior import build_prior_snapshot


def test_prior_snapshot_contract_normalizes_and_keeps_abc() -> None:
    payload = build_prior_snapshot(
        pack_id="strategic_actor_nokia_v1",
        pack_version="1.0.0",
        situation_id="nokia-elop-2010",
        actor_ref="actors/steve-jobs.md",
        raw_prior_scores=[
            {"scenario_key": "A", "score": 0.4},
            {"scenario_key": "B", "score": 0.35},
            {"scenario_key": "C", "score": 0.25},
        ],
        planning_query_ref="data/scenarios/strategic_actor_nokia_v1/traces/planning_query.json",
    )

    assert payload["snapshot_version"] == "prior_snapshot_v1"
    assert [item["scenario_key"] for item in payload["raw_prior_scores"]] == ["A", "B", "C"]
    assert [item["scenario_key"] for item in payload["normalized_priors"]] == ["A", "B", "C"]

    total = sum(float(item["score"]) for item in payload["normalized_priors"])
    assert abs(total - 1.0) < 1e-6
