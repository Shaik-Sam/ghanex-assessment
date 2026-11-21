import io
import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from rag.errors import (
    CorruptDocumentError,
    EmptyDocumentError,
    EncryptedDocumentError,
    FileTooLargeError,
    UnsupportedFormatError,
)
from rag.models import Page

PDF_MAGIC = b"%PDF-"


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def validate_upload(name: str, data: bytes, max_mb: int) -> None:
    if not name.lower().endswith(".pdf"):
        raise UnsupportedFormatError(
            f"'{name}' is not a PDF. Only .pdf files are supported."
        )
    if not data:
        raise EmptyDocumentError(f"'{name}' is an empty file.")
    if len(data) > max_mb * 1024 * 1024:
        raise FileTooLargeError(f"'{name}' is larger than the {max_mb} MB limit.")
    if not data.lstrip()[:5] == PDF_MAGIC:
        raise UnsupportedFormatError(
            f"'{name}' does not look like a valid PDF file."
        )


def extract_pages(name: str, data: bytes, max_mb: int = 25) -> list[Page]:
    validate_upload(name, data, max_mb)

    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as exc:
        raise CorruptDocumentError(f"'{name}' could not be read: {exc}") from exc
    except Exception as exc:
        raise CorruptDocumentError(f"'{name}' could not be opened: {exc}") from exc

    if reader.is_encrypted:
        try:
            unlocked = reader.decrypt("")
        except Exception:
            unlocked = 0
        if not unlocked:
            raise EncryptedDocumentError(
                f"'{name}' is password protected. Remove the password and upload it again."
            )

    pages: list[Page] = []
    try:
        for number, pdf_page in enumerate(reader.pages, start=1):
            try:
                raw = pdf_page.extract_text() or ""
            except Exception:
                raw = ""
            text = clean_text(raw)
            if text:
                pages.append(Page(document=name, number=number, text=text))
    except Exception as exc:
        raise CorruptDocumentError(f"'{name}' has unreadable pages: {exc}") from exc

    if not pages:
        raise EmptyDocumentError(
            f"No extractable text found in '{name}'. It may be a scanned document or contain only images."
        )
    return pages
