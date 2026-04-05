from pathlib import Path

from omen.cli.situation import (
    _derive_case_name_from_path,
    _derive_default_pack_id,
    _derive_pack_id_from_situation_artifact,
    _resolve_default_output_path,
    _resolve_generation_trace_output_path,
    _resolve_splitter_default_output_path,
)


def test_case_pack_id_without_actor_uses_case_prefix_only() -> None:
    input_path = Path("cases/situations/nokia-elop-2010.md")
    assert _derive_case_name_from_path(input_path) == "nokia"
    assert _derive_default_pack_id(input_path, actor_ref=None) == "nokia_v1"


def test_case_pack_id_with_actor_uses_strategic_actor_prefix() -> None:
    input_path = Path("cases/situations/nokia-elop-2010.md")
    assert _derive_default_pack_id(input_path, actor_ref="actors/steve-jobs.md") == "strategic_actor_nokia_v1"


def test_scenario_pack_id_infers_actor_context_from_situation_artifact() -> None:
    situation_artifact = {
        "source_meta": {
            "source_path": "cases/situations/nokia-elop-2010.md",
            "actor_ref": "actors/steve-jobs.md",
        }
    }
    pack_id = _derive_pack_id_from_situation_artifact(
        situation_artifact,
        Path("data/scenarios/nokia_v1/nokia-elop-2010_situation.json"),
    )
    assert pack_id == "strategic_actor_nokia_v1"


def test_default_output_paths_follow_pack_id() -> None:
    analyze_output = _resolve_default_output_path(
        Path("cases/situations/nokia-elop-2010.md"),
        "nokia_v1",
    )
    scenario_output = _resolve_splitter_default_output_path(
        Path("data/scenarios/nokia_v1/nokia-elop-2010_situation.json"),
        "nokia_v1",
    )

    assert analyze_output == Path("data/scenarios/nokia_v1/nokia-elop-2010_situation.json")
    assert scenario_output == Path("data/scenarios/nokia_v1/nokia-elop-2010.json")


def test_generation_trace_path_uses_generation_suffix() -> None:
    trace_output = _resolve_generation_trace_output_path(
        Path("data/scenarios/nokia_v1/nokia-elop-2010_situation.json")
    )
    assert trace_output == Path("data/scenarios/nokia_v1/nokia-elop-2010_generation.json")
