import pytest

from rag.chunker import chunk_pages, split_text
from rag.models import Page


def test_short_text_is_single_chunk():
    assert split_text("Hello world.", 100, 20) == ["Hello world."]


def test_chunks_respect_size_limit():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = split_text(text, 200, 40)
    assert len(chunks) > 1
    assert all(len(chunk) <= 200 for chunk in chunks)


def test_consecutive_chunks_overlap():
    text = ". ".join(f"Sentence number {i} is here" for i in range(60)) + "."
    chunks = split_text(text, 200, 60)
    overlaps = 0
    for left, right in zip(chunks, chunks[1:]):
        tail_words = set(left.split()[-4:])
        if tail_words & set(right.split()[:12]):
            overlaps += 1
    assert overlaps >= len(chunks) - 2


def test_no_text_is_lost():
    words = [f"w{i}" for i in range(300)]
    chunks = split_text(" ".join(words), 150, 30)
    joined = " ".join(chunks)
    assert all(word in joined for word in words)


def test_long_unbroken_token_is_hard_split():
    chunks = split_text("x" * 1000, 300, 50)
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert sum(len(chunk) for chunk in chunks) >= 1000


def test_paragraph_boundaries_preferred():
    text = ("A" * 80 + "\n\n") + ("B" * 80 + "\n\n") + ("C" * 80)
    chunks = split_text(text, 100, 0)
    assert chunks == ["A" * 80, "B" * 80, "C" * 80]


@pytest.mark.parametrize("size,overlap", [(0, 0), (100, 100), (100, -1), (50, 80)])
def test_invalid_parameters(size, overlap):
    with pytest.raises(ValueError):
        split_text("text", size, overlap)


def test_chunk_pages_preserves_page_numbers_and_global_index():
    pages = [Page("a.pdf", 1, "First page text."), Page("a.pdf", 3, "Third page text.")]
    chunks = chunk_pages(pages, 100, 10)
    assert [c.page for c in chunks] == [1, 3]
    assert [c.index for c in chunks] == [0, 1]
