import numpy as np
import pytest

from rag.models import Chunk
from rag.store import VectorStore


def unit(*values):
    vector = np.array(values, dtype="float32")
    return vector / np.linalg.norm(vector)


def chunk(doc, index, text="t"):
    return Chunk(document=doc, page=1, index=index, text=text)


def test_search_returns_most_similar_first():
    store = VectorStore()
    vectors = np.vstack([unit(1, 0, 0), unit(0, 1, 0), unit(0.9, 0.1, 0)])
    store.add_document("a.pdf", [chunk("a.pdf", i, f"c{i}") for i in range(3)], vectors)
    results = store.search(unit(1, 0, 0), k=2)
    assert [r.text for r in results] == ["c0", "c2"]
    assert results[0].score == pytest.approx(1.0, abs=1e-5)


def test_min_score_filters_results():
    store = VectorStore()
    store.add_document("a.pdf", [chunk("a.pdf", 0), chunk("a.pdf", 1)], np.vstack([unit(1, 0), unit(0, 1)]))
    assert len(store.search(unit(1, 0), k=5, min_score=0.5)) == 1


def test_index_refreshes_when_document_added_and_removed():
    store = VectorStore()
    store.add_document("a.pdf", [chunk("a.pdf", 0, "from a")], np.vstack([unit(1, 0)]))
    store.add_document("b.pdf", [chunk("b.pdf", 0, "from b")], np.vstack([unit(0, 1)]))
    assert store.size == 2
    assert store.search(unit(0, 1), k=1)[0].document == "b.pdf"
    store.remove_document("b.pdf")
    assert store.size == 1
    assert store.documents == ["a.pdf"]
    assert all(r.document == "a.pdf" for r in store.search(unit(0, 1), k=5))


def test_replacing_document_does_not_duplicate_chunks():
    store = VectorStore()
    store.add_document("a.pdf", [chunk("a.pdf", 0)], np.vstack([unit(1, 0)]))
    store.add_document("a.pdf", [chunk("a.pdf", 0), chunk("a.pdf", 1)], np.vstack([unit(1, 0), unit(0, 1)]))
    assert store.size == 2


def test_empty_store_returns_nothing():
    store = VectorStore()
    assert store.search(unit(1, 0), k=3) == []
    store.add_document("a.pdf", [chunk("a.pdf", 0)], np.vstack([unit(1, 0)]))
    store.clear()
    assert store.size == 0
    assert store.search(unit(1, 0), k=3) == []


def test_length_mismatch_rejected():
    store = VectorStore()
    with pytest.raises(ValueError):
        store.add_document("a.pdf", [chunk("a.pdf", 0)], np.vstack([unit(1, 0), unit(0, 1)]))
