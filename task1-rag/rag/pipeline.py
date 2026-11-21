import hashlib
from typing import Protocol

from rag.chunker import chunk_pages
from rag.config import Settings
from rag.embedder import Embedder
from rag.errors import NoDocumentsError, RagError
from rag.generator import NOT_FOUND_MESSAGE
from rag.loader import extract_pages
from rag.models import Answer, IngestResult
from rag.store import VectorStore


class Generator(Protocol):
    def generate(self, question: str, sources: list, history: list[dict[str, str]]) -> str: ...


class DocumentAssistant:
    def __init__(self, embedder: Embedder, generator: Generator, settings: Settings):
        self.embedder = embedder
        self.generator = generator
        self.settings = settings
        self.store = VectorStore()
        self._fingerprints: dict[str, str] = {}
        self.history: list[dict[str, str]] = []

    @property
    def documents(self) -> list[str]:
        return self.store.documents

    def ingest(self, name: str, data: bytes) -> IngestResult:
        fingerprint = hashlib.sha256(data).hexdigest()
        if self._fingerprints.get(name) == fingerprint:
            return IngestResult(document=name, skipped=True)

        try:
            pages = extract_pages(name, data, self.settings.max_upload_mb)
            chunks = chunk_pages(
                pages, self.settings.chunk_size, self.settings.chunk_overlap
            )
            vectors = self.embedder.embed_documents([chunk.text for chunk in chunks])
        except RagError as exc:
            return IngestResult(document=name, error=str(exc))
        except Exception as exc:
            return IngestResult(document=name, error=f"Unexpected error while indexing: {exc}")

        self.store.add_document(name, chunks, vectors)
        self._fingerprints[name] = fingerprint
        return IngestResult(document=name, pages=len(pages), chunks=len(chunks))

    def remove(self, name: str) -> None:
        self.store.remove_document(name)
        self._fingerprints.pop(name, None)

    def reset(self) -> None:
        self.store.clear()
        self._fingerprints.clear()
        self.history.clear()

    def ask(self, question: str) -> Answer:
        question = question.strip()
        if not question:
            raise RagError("Please enter a question.")
        if self.store.size == 0:
            raise NoDocumentsError("Upload and process at least one PDF before asking questions.")

        query_vector = self.embedder.embed_query(question)
        sources = self.store.search(
            query_vector, self.settings.top_k, self.settings.min_score
        )
        if not sources:
            return Answer(text=NOT_FOUND_MESSAGE, sources=[], grounded=False)

        window = self.settings.max_history_turns * 2
        text = self.generator.generate(question, sources, self.history[-window:])
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": text})
        return Answer(text=text, sources=sources, grounded=NOT_FOUND_MESSAGE not in text)
