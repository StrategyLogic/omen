"""PDF page-slice extraction adapter for ingest workflows.

This module intentionally keeps PDF dependency optional to avoid hard runtime
requirements for users who do not run ingest features.
"""

from __future__ import annotations

from pathlib import Path


def extract_pdf_pages(
    pdf_path: str | Path,
    *,
    start_page: int = 1,
    end_page: int | None = None,
) -> str:
    """Extract text from a page range in a PDF.

    Pages are 1-based inclusive.
    """

    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError(
            "PDF extraction requires `pypdf` from Omen project dependencies. "
            "Please reinstall the local environment in editable mode."
        ) from exc

    path = Path(pdf_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    reader = PdfReader(str(path))
    total = len(reader.pages)
    if total == 0:
        return ""

    ps = max(1, start_page)
    pe = min(end_page if end_page is not None else total, total)

    if pe < ps:
        raise ValueError("end_page must be >= start_page")

    pages = [reader.pages[i - 1].extract_text() or "" for i in range(ps, pe + 1)]
    return "\n".join(pages)
