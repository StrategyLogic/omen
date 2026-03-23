"""Case selection helpers for Spec 6 UI and artifact layout."""

from __future__ import annotations

from pathlib import Path


def normalize_case_id(value: str | Path) -> str:
    return Path(str(value)).stem.strip().lower()


def case_id_from_markdown(file_path: Path) -> str:
    return normalize_case_id(file_path)


def list_case_ids_from_cases(cases_root: str | Path = "cases") -> list[str]:
    root = Path(cases_root)
    if not root.exists() or not root.is_dir():
        return []

    case_ids = {
        case_id_from_markdown(item)
        for item in root.glob("*.md")
        if item.is_file()
    }
    return sorted(item for item in case_ids if item)


def default_case_id(case_ids: list[str], loaded_case_id: str | Path | None = None) -> str:
    normalized_loaded_case_id = normalize_case_id(loaded_case_id or "")
    if normalized_loaded_case_id and normalized_loaded_case_id in case_ids:
        return normalized_loaded_case_id
    if case_ids:
        return case_ids[0]
    return ""


def case_output_dir(case_id: str, output_root: str | Path = "output/case_replay") -> Path:
    return Path(output_root) / normalize_case_id(case_id)


def resolve_existing_case_output_dir(case_id: str, output_root: str | Path = "output/case_replay") -> Path:
    return case_output_dir(case_id, output_root=output_root)


def suggest_document_path(case_id: str) -> str:
    return str(Path("cases") / f"{normalize_case_id(case_id)}.md")


def suggest_strategy(case_id: str) -> str:
    return "new_tech_market_entry"


def suggest_known_outcome(case_id: str) -> str:
    return "unknown"


def case_display_title(case_id: str) -> str:
    case_name = normalize_case_id(case_id)
    return case_name.replace("-", " ").replace("_", " ").title()