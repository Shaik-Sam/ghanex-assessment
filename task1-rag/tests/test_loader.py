import pytest

from rag.errors import (
    CorruptDocumentError,
    EmptyDocumentError,
    EncryptedDocumentError,
    FileTooLargeError,
    UnsupportedFormatError,
)
from rag.loader import clean_text, extract_pages
from tests.conftest import blank_pdf, encrypted_pdf, make_pdf


def test_extracts_text_per_page():
    pages = extract_pages("doc.pdf", make_pdf(["Alpha content here", "Beta content here"]))
    assert [p.number for p in pages] == [1, 2]
    assert "Alpha" in pages[0].text
    assert "Beta" in pages[1].text
    assert pages[0].document == "doc.pdf"


def test_rejects_non_pdf_extension():
    with pytest.raises(UnsupportedFormatError):
        extract_pages("notes.txt", b"hello")


def test_rejects_fake_pdf_content():
    with pytest.raises(UnsupportedFormatError):
        extract_pages("fake.pdf", b"this is not a pdf")


def test_rejects_empty_file():
    with pytest.raises(EmptyDocumentError):
        extract_pages("empty.pdf", b"")


def test_rejects_oversized_file():
    with pytest.raises(FileTooLargeError):
        extract_pages("big.pdf", b"%PDF-" + b"0" * (2 * 1024 * 1024), max_mb=1)


def test_blank_pdf_reports_no_text():
    with pytest.raises(EmptyDocumentError):
        extract_pages("scan.pdf", blank_pdf())


def test_encrypted_pdf_reports_password():
    with pytest.raises(EncryptedDocumentError):
        extract_pages("locked.pdf", encrypted_pdf())


def test_corrupt_pdf_reports_error():
    with pytest.raises((CorruptDocumentError, EmptyDocumentError)):
        extract_pages("broken.pdf", b"%PDF-1.4\ngarbage that is not a real structure")


def test_clean_text_normalises_whitespace_and_hyphenation():
    assert clean_text("inter-\nnational   trade\n\n\n\nrules") == "international trade\n\nrules"
