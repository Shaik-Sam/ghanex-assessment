from dataclasses import dataclass, field


@dataclass(frozen=True)
class Page:
    document: str
    number: int
    text: str


@dataclass(frozen=True)
class Chunk:
    document: str
    page: int
    index: int
    text: str


@dataclass(frozen=True)
class Source:
    document: str
    page: int
    chunk_index: int
    score: float
    text: str


@dataclass
class Answer:
    text: str
    sources: list[Source] = field(default_factory=list)
    grounded: bool = True


@dataclass
class IngestResult:
    document: str
    pages: int = 0
    chunks: int = 0
    skipped: bool = False
    error: str | None = None
