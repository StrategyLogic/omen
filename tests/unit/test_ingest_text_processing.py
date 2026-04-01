from omen.ingest.documents import clean_text, split_into_chunks


def test_clean_text_merges_soft_line_breaks() -> None:
    raw = "AI mem-\nory improves\nretrieval.\n\nNext paragraph."
    cleaned = clean_text(raw)
    assert "memory improves retrieval." in cleaned
    assert "retrieval.\n\nNext paragraph." in cleaned


def test_split_into_chunks_has_overlap() -> None:
    text = "abcdefghij"
    chunks = split_into_chunks(text, chunk_size=4, chunk_overlap=1)
    assert chunks == ["abcd", "defg", "ghij"]


def test_split_into_chunks_rejects_invalid_overlap() -> None:
    try:
        split_into_chunks("abc", chunk_size=3, chunk_overlap=3)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "chunk_overlap" in str(exc)
