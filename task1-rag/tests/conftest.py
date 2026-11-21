import hashlib
import io

import numpy as np
import pytest
from pypdf import PdfWriter

from rag.embedder import normalize


class HashEmbedder:
    dim = 64

    def _vector(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dim, dtype="float32")
        for token in text.lower().split():
            digest = hashlib.md5(token.strip(".,?!").encode()).digest()
            vector[digest[0] % self.dim] += 1.0
        return vector

    def embed_documents(self, texts):
        return normalize(np.vstack([self._vector(t) for t in texts]))

    def embed_query(self, text):
        return normalize(np.vstack([self._vector(text)]))


class EchoGenerator:
    def __init__(self):
        self.calls = []

    def generate(self, question, sources, history):
        self.calls.append((question, sources, history))
        return f"answer based on {len(sources)} passages [1]"


def make_pdf(pages: list[str]) -> bytes:
    objects = []
    kids = []
    objects.append(None)
    objects.append(None)
    font_id = 3
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for text in pages:
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 50 750 Td ({safe}) Tj ET".encode()
        content_id = len(objects) + 1
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
        page_id = len(objects) + 1
        kids.append(page_id)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_id} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode()
        )
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kid_refs = " ".join(f"{k} 0 R" for k in kids)
    objects[1] = f"<< /Type /Pages /Kids [{kid_refs}] /Count {len(kids)} >>".encode()

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return out.getvalue()


def blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def encrypted_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("secret")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture
def embedder():
    return HashEmbedder()


@pytest.fixture
def generator():
    return EchoGenerator()
