"""URL ingest helpers for fetching and storing situation source text."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from omen.ingest.processor.text import clean_text


DEFAULT_URL_SOURCE_DIR = Path("data/ingest/source")
_BLOCK_TAGS = {
    "article",
    "aside",
    "blockquote",
    "br",
    "div",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "li",
    "main",
    "p",
    "section",
    "title",
    "tr",
    "ul",
    "ol",
}


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth == 0 and lowered in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if self._skip_depth == 0 and lowered in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def _slugify_url(url: str) -> str:
    parsed = urlparse(url)
    base = f"{parsed.netloc}{parsed.path}".strip().lower()
    base = re.sub(r"[^a-z0-9]+", "-", base)
    base = re.sub(r"-+", "-", base).strip("-")
    return base or "source"


def fetch_url_text(url: str, *, timeout: int = 20) -> str:
    parsed = urlparse(str(url).strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must use http or https")

    request = Request(
        str(url).strip(),
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; Omen/0.2.0; +https://github.com/)"
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw_bytes = response.read()
        content_type = str(response.headers.get("Content-Type") or "").lower()
        charset = response.headers.get_content_charset() or "utf-8"

    raw_text = raw_bytes.decode(charset, errors="replace")
    if "html" in content_type or "<html" in raw_text.lower():
        parser = _HTMLTextExtractor()
        parser.feed(raw_text)
        extracted = parser.get_text()
    else:
        extracted = raw_text

    normalized = clean_text(extracted)
    if not normalized:
        raise ValueError("URL content did not contain usable text")
    return normalized


def save_url_source_text(
    *,
    url: str,
    text: str,
    source_dir: str | Path = DEFAULT_URL_SOURCE_DIR,
) -> Path:
    root = Path(source_dir)
    root.mkdir(parents=True, exist_ok=True)
    output_path = root / f"{_slugify_url(url)}.txt"
    output_path.write_text(clean_text(text), encoding="utf-8")
    return output_path