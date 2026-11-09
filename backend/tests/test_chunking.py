from app.services.chunking import split_text


def test_split_text_empty() -> None:
    assert split_text("") == []
    assert split_text("   ") == []


def test_split_text_respects_size_and_overlap() -> None:
    text = "word " * 50
    chunks = split_text(text, chunk_size=40, chunk_overlap=10)
    assert len(chunks) >= 2
    assert all(len(chunk) <= 40 for chunk in chunks)
