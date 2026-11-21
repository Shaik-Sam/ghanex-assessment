import faiss
import numpy as np

from rag.models import Chunk, Source


class VectorStore:
    def __init__(self):
        self._entries: dict[str, tuple[list[Chunk], np.ndarray]] = {}
        self._index: faiss.Index | None = None
        self._flat: list[Chunk] = []

    @property
    def documents(self) -> list[str]:
        return list(self._entries)

    @property
    def size(self) -> int:
        return len(self._flat)

    def has_document(self, name: str) -> bool:
        return name in self._entries

    def add_document(self, name: str, chunks: list[Chunk], vectors: np.ndarray) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        self._entries[name] = (chunks, np.asarray(vectors, dtype="float32"))
        self._rebuild()

    def remove_document(self, name: str) -> None:
        if name in self._entries:
            del self._entries[name]
            self._rebuild()

    def clear(self) -> None:
        self._entries.clear()
        self._rebuild()

    def _rebuild(self) -> None:
        self._flat = []
        matrices = []
        for chunks, vectors in self._entries.values():
            self._flat.extend(chunks)
            matrices.append(vectors)

        if not matrices:
            self._index = None
            return

        stacked = np.vstack(matrices)
        index = faiss.IndexFlatIP(stacked.shape[1])
        index.add(stacked)
        self._index = index

    def search(self, query_vector: np.ndarray, k: int, min_score: float = 0.0) -> list[Source]:
        if self._index is None or not self._flat:
            return []
        k = min(k, len(self._flat))
        query = np.asarray(query_vector, dtype="float32").reshape(1, -1)
        scores, ids = self._index.search(query, k)

        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0 or score < min_score:
                continue
            chunk = self._flat[idx]
            results.append(
                Source(
                    document=chunk.document,
                    page=chunk.page,
                    chunk_index=chunk.index,
                    score=float(score),
                    text=chunk.text,
                )
            )
        return results
