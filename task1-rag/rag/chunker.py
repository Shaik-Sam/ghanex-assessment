from rag.models import Chunk, Page

SEPARATORS = ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ")


def _split_on(text: str, separator: str) -> list[str]:
    parts = text.split(separator)
    pieces = []
    for position, part in enumerate(parts):
        if position < len(parts) - 1:
            pieces.append(part + separator)
        elif part:
            pieces.append(part)
    return pieces


def _recursive_split(text: str, size: int, separators: tuple[str, ...]) -> list[str]:
    if len(text) <= size:
        return [text] if text.strip() else []
    if not separators:
        return [text[i : i + size] for i in range(0, len(text), size)]

    head, rest = separators[0], separators[1:]
    pieces = _split_on(text, head)
    if len(pieces) == 1:
        return _recursive_split(text, size, rest)

    result: list[str] = []
    for piece in pieces:
        if len(piece) > size:
            result.extend(_recursive_split(piece, size, rest))
        else:
            result.append(piece)
    return result


def _merge(pieces: list[str], size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    length = 0

    for piece in pieces:
        if current and length + len(piece) > size:
            chunks.append("".join(current).strip())
            while current and (length > overlap or length + len(piece) > size):
                length -= len(current[0])
                current.pop(0)
        current.append(piece)
        length += len(piece)

    if current:
        tail = "".join(current).strip()
        if tail and (not chunks or tail != chunks[-1]):
            chunks.append(tail)
    return [chunk for chunk in chunks if chunk]


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")
    pieces = _recursive_split(text, chunk_size, SEPARATORS)
    return _merge(pieces, chunk_size, chunk_overlap)


def chunk_pages(pages: list[Page], chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        for text in split_text(page.text, chunk_size, chunk_overlap):
            chunks.append(
                Chunk(
                    document=page.document,
                    page=page.number,
                    index=len(chunks),
                    text=text,
                )
            )
    return chunks
