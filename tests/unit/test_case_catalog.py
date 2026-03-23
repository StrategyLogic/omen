from pathlib import Path

from omen.ui.case_catalog import (
    case_display_title,
    case_id_from_markdown,
    case_output_dir,
    default_case_id,
    list_case_ids_from_cases,
    normalize_case_id,
    resolve_existing_case_output_dir,
    suggest_document_path,
)


def test_normalize_case_id_supports_canonical_and_legacy_names() -> None:
    assert normalize_case_id("xd") == "xd"
    assert normalize_case_id("cases/xd.md") == "xd"
    assert normalize_case_id("case-xd") == "case-xd"
    assert normalize_case_id("x-developer") == "x-developer"
    assert normalize_case_id("x-developer-replay") == "x-developer-replay"
    assert normalize_case_id("shenda-replay") == "shenda-replay"


def test_case_id_from_markdown_uses_case_stem_without_prefix() -> None:
    assert case_id_from_markdown(Path("cases/xd.md")) == "xd"
    assert case_id_from_markdown(Path("cases/x-developer.md")) == "x-developer"
    assert case_id_from_markdown(Path("cases/case-xd.md")) == "case-xd"


def test_default_case_id_prefers_first_markdown_when_nothing_loaded() -> None:
    assert default_case_id(["ontology", "shenda", "xd"], None) == "ontology"
    assert default_case_id(["ontology", "shenda", "xd"], "") == "ontology"
    assert default_case_id(["ontology", "shenda", "xd"], "xd") == "xd"


def test_list_case_ids_from_cases_reads_only_cases_markdown(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    output_dir = tmp_path / "output" / "case_replay" / "x-developer"
    cases_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    (cases_dir / "x-developer.md").write_text("# xd", encoding="utf-8")
    (cases_dir / "shenda.md").write_text("# shenda", encoding="utf-8")
    (cases_dir / "vector-memory-source.md").write_text("# included", encoding="utf-8")
    (output_dir / "strategy_ontology.json").write_text("{}", encoding="utf-8")

    assert list_case_ids_from_cases(cases_dir) == ["shenda", "vector-memory-source", "x-developer"]


def test_resolve_existing_case_output_dir_uses_case_name_directory(tmp_path: Path) -> None:
    output_root = tmp_path / "output" / "case_replay"
    target_dir = output_root / "x-developer"
    target_dir.mkdir(parents=True)

    assert case_output_dir("x-developer", output_root=output_root) == target_dir
    assert resolve_existing_case_output_dir("x-developer", output_root=output_root) == target_dir


def test_case_metadata_helpers_follow_canonical_case_names() -> None:
    assert suggest_document_path("x-developer") == "cases/x-developer.md"
    assert suggest_document_path("shenda") == "cases/shenda.md"
    assert case_display_title("x-developer") == "X Developer"