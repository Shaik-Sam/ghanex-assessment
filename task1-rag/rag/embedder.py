from typing import Protocol

import numpy as np


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> np.ndarray: ...

    def embed_query(self, text: str) -> np.ndarray: ...


def normalize(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype="float32")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class FastEmbedder:
    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        vectors = list(self._model.passage_embed(texts))
        return normalize(np.vstack(vectors))

    def embed_query(self, text: str) -> np.ndarray:
        vectors = list(self._model.query_embed(text))
        return normalize(np.vstack(vectors))
