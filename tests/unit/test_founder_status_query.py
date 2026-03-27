from omen.analysis.founder.query import build_status_snapshot


def test_build_status_snapshot_filters_timeline_and_builds_graph():
    strategy_ontology = {
        "abox": {
            "events": [
                {
                    "event_id": "event.2016.pivot",
                    "time": "2016-05",
                    "event": "Pivoted strategy",
                    "evidence_refs": ["doc:1"],
                    "confidence": "high",
                    "is_strategy_related": True,
                },
                {
                    "event_id": "event.2018.expand",
                    "time": "2018-01",
                    "event": "Expanded overseas",
                    "evidence_refs": ["doc:2"],
                    "confidence": "medium",
                    "is_strategy_related": True,
                },
            ]
        }
    }
    founder_ontology = {
        "actors": [{"id": "founder.xd", "name": "Founder"}],
        "events": [
            {
                "id": "decision.2016.pivot",
                "date": "2016-05",
                "type": "pivot_decision",
                "actors_involved": ["founder.xd"],
                "decision": {"response_to": ["constraint.capital"]},
            }
        ],
        "constraints": [{"id": "constraint.capital", "category": "capital"}],
        "influences": [
            {
                "source": "event_decision.2016.pivot",
                "target": "constraint.capital",
                "type": "validates",
            }
        ],
    }

    payload = build_status_snapshot(
        strategy_ontology=strategy_ontology,
        founder_ontology=founder_ontology,
        year=2016,
    )

    assert payload["summary"]["timeline_event_count"] == 1
    assert payload["timeline"][0]["event_id"] == "decision.2016.pivot"
    assert payload["timeline"][0]["event"] == "pivot_decision"

    graph = payload["founder_graph"]
    node_ids = {node["id"] for node in graph["nodes"]}
    assert "founder.xd" in node_ids
    assert "decision.2016.pivot" in node_ids
    assert "constraint.capital" in node_ids

    constraint_node = next(node for node in graph["nodes"] if node["id"] == "constraint.capital")
    assert constraint_node["label"] == "capital"

    edge_labels = [edge["label"] for edge in graph["edges"]]
    assert "validates" in edge_labels
    assert payload["summary"]["founder_node_count"] >= 3
    assert payload["summary"]["founder_edge_count"] >= 1


def test_build_status_snapshot_falls_back_to_founder_timeline_when_strategy_events_missing():
    strategy_ontology = {"abox": {"events": []}}
    founder_ontology = {
        "actors": [{"id": "actor_xd", "name": "X-Developer team", "type": "company"}],
        "events": [
            {
                "id": "xd-1",
                "time": "2016",
                "event": "X-Developer platform launched",
                "actors_involved": ["actor_xd"],
                "evidence_refs": ["doc:1"],
                "confidence": 0.9,
                "is_strategy_related": True,
            }
        ],
        "constraints": [],
        "influences": [],
    }

    payload = build_status_snapshot(
        strategy_ontology=strategy_ontology,
        founder_ontology=founder_ontology,
        year=2016,
    )

    assert payload["summary"]["timeline_event_count"] == 1
    assert payload["timeline"][0]["event_id"] == "xd-1"
    assert payload["timeline"][0]["event"] == "launch"


def test_build_status_snapshot_uses_legacy_content_when_description_missing():
    strategy_ontology = {"abox": {"events": []}}
    founder_ontology = {
        "actors": [{"id": "actor_xd", "name": "X-Developer team", "type": "company"}],
        "events": [
            {
                "id": "xd-legacy-1",
                "time": "2016",
                "name": "Product launch",
                "content": "Founder shipped the first product after repeated market tests.",
                "actors_involved": ["actor_xd"],
                "is_strategy_related": True,
            }
        ],
        "constraints": [],
        "influences": [],
    }

    payload = build_status_snapshot(
        strategy_ontology=strategy_ontology,
        founder_ontology=founder_ontology,
        year=2016,
    )

    assert payload["timeline"][0]["description"] == "Founder shipped the first product after repeated market tests."
    assert payload["timeline"][0]["content"] == "Founder shipped the first product after repeated market tests."
    assert payload["timeline"][0]["is_strategy_related"] is True


def test_build_founder_graph_uses_only_explicit_edges_and_keeps_all_nodes():
    strategy_ontology = {"abox": {"events": []}}
    founder_ontology = {
        "meta": {"case_id": "x-developer"},
        "actors": [
            {"id": "actor-xdev-team", "name": "X-Developer Team", "type": "organization"},
            {"id": "actor-enterprise-leaders", "name": "Enterprise Leaders", "type": "role"},
        ],
        "events": [],
        "constraints": [
            {
                "id": "constraint-1",
                "type": "market_positioning",
                "applies_to": ["actor-xdev-team"],
            }
        ],
        "influences": [],
    }

    payload = build_status_snapshot(
        strategy_ontology=strategy_ontology,
        founder_ontology=founder_ontology,
        year=None,
    )

    graph = payload["founder_graph"]
    edges = graph["edges"]
    node_ids = {node["id"] for node in graph["nodes"]}

    assert any(
        edge["source"] == "constraint-1"
        and edge["target"] == "actor-xdev-team"
        and edge["label"] == "constraints"
        for edge in edges
    )
    assert "actor-enterprise-leaders" in node_ids


def test_build_founder_graph_handles_legacy_constraint_event_influence_keys():
    strategy_ontology = {"abox": {"events": []}}
    founder_ontology = {
        "meta": {"case_id": "x-developer"},
        "actors": [{"id": "actor-founder", "name": "Founder", "type": "founder"}],
        "products": [{"id": "product-xdev", "name": "X-Developer", "type": "platform"}],
        "events": [{"id": "xdev-1", "time": "2019", "type": "launch", "actors_involved": ["actor-founder"]}],
        "constraints": [{"id": "constraint-1", "type": "market_adoption", "actors_affected": ["actor-founder"]}],
        "influences": [
            {
                "source_event": "xdev-1",
                "target_constraint": "constraint-1",
                "type": "mitigates",
            }
        ],
    }

    payload = build_status_snapshot(
        strategy_ontology=strategy_ontology,
        founder_ontology=founder_ontology,
        year=None,
    )

    graph = payload["founder_graph"]
    node_ids = {node["id"] for node in graph["nodes"]}
    assert "product-xdev" in node_ids

    assert any(
        edge["source"] == "constraint-1"
        and edge["target"] == "actor-founder"
        and edge["label"] == "constraints"
        for edge in graph["edges"]
    )
    assert any(
        edge["source"] == "xdev-1"
        and edge["target"] == "constraint-1"
        and edge["label"] == "mitigates"
        for edge in graph["edges"]
    )


def test_build_founder_graph_adds_constraint_edge_to_founder_by_default():
    strategy_ontology = {"abox": {"events": []}}
    founder_ontology = {
        "meta": {"case_id": "x-developer"},
        "actors": [
            {"id": "actor-founders", "name": "Founder Team", "type": "organization"},
            {"id": "actor-customer", "name": "Customer", "type": "customer"},
        ],
        "events": [],
        "constraints": [
            {
                "id": "constraint-adoption",
                "type": "market_adoption",
                "actors_affected": ["actor-customer"],
            }
        ],
        "influences": [],
    }

    payload = build_status_snapshot(
        strategy_ontology=strategy_ontology,
        founder_ontology=founder_ontology,
        year=None,
    )

    graph = payload["founder_graph"]
    assert any(
        edge["source"] == "constraint-adoption"
        and edge["target"] == "actor-founders"
        and edge["label"] == "constraints"
        for edge in graph["edges"]
    )
