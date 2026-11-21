import pytest

from rag.config import Settings
from rag.errors import NoDocumentsError, RagError
from rag.generator import NOT_FOUND_MESSAGE, build_context, build_messages
from rag.pipeline import DocumentAssistant
from tests.conftest import blank_pdf, make_pdf

SETTINGS = Settings(chunk_size=200, chunk_overlap=40, top_k=3, min_score=0.1)


@pytest.fixture
def assistant(embedder, generator):
    return DocumentAssistant(embedder, generator, SETTINGS)


def test_ingest_indexes_document(assistant):
    result = assistant.ingest("a.pdf", make_pdf(["Paris is the capital of France"]))
    assert result.error is None
    assert result.pages == 1
    assert result.chunks >= 1
    assert assistant.documents == ["a.pdf"]


def test_ingest_reports_errors_without_raising(assistant):
    assert "scanned" in assistant.ingest("scan.pdf", blank_pdf()).error
    assert assistant.ingest("x.txt", b"data").error
    assert assistant.documents == []


def test_unchanged_file_is_skipped_and_changed_file_is_reindexed(assistant):
    data = make_pdf(["Original text about cats"])
    assert not assistant.ingest("a.pdf", data).skipped
    assert assistant.ingest("a.pdf", data).skipped
    changed = assistant.ingest("a.pdf", make_pdf(["Different text about dogs"]))
    assert not changed.skipped
    assert assistant.store.size == changed.chunks


def test_ask_without_documents_raises(assistant):
    with pytest.raises(NoDocumentsError):
        assistant.ask("anything?")


def test_ask_rejects_blank_question(assistant):
    assistant.ingest("a.pdf", make_pdf(["Some text"]))
    with pytest.raises(RagError):
        assistant.ask("   ")


def test_ask_returns_sources_with_references(assistant, generator):
    assistant.ingest("france.pdf", make_pdf(["Paris is the capital of France", "Berlin is the capital of Germany"]))
    answer = assistant.ask("What is the capital of France?")
    assert answer.sources
    assert answer.sources[0].document == "france.pdf"
    assert answer.sources[0].page in (1, 2)
    assert generator.calls[0][0] == "What is the capital of France?"
    assert answer.grounded


def test_no_relevant_chunks_short_circuits_llm(embedder, generator):
    strict = DocumentAssistant(embedder, generator, Settings(chunk_size=200, chunk_overlap=40, min_score=0.99))
    strict.ingest("a.pdf", make_pdf(["completely unrelated astronomy text"]))
    answer = strict.ask("quantum chromodynamics lattice")
    assert answer.text == NOT_FOUND_MESSAGE
    assert not answer.grounded
    assert generator.calls == []


def test_history_is_forwarded_on_followups(assistant, generator):
    assistant.ingest("a.pdf", make_pdf(["Paris is the capital of France"]))
    assistant.ask("capital of France")
    assistant.ask("capital of France again")
    assert generator.calls[1][2][0] == {"role": "user", "content": "capital of France"}


def test_removing_document_removes_it_from_retrieval(assistant):
    assistant.ingest("a.pdf", make_pdf(["alpha beta gamma"]))
    assistant.ingest("b.pdf", make_pdf(["delta epsilon zeta"]))
    assistant.remove("a.pdf")
    answer = assistant.ask("alpha beta gamma")
    assert all(s.document == "b.pdf" for s in answer.sources)


def test_prompt_contains_numbered_sources_and_grounding_rule(assistant):
    assistant.ingest("a.pdf", make_pdf(["Paris is the capital of France"]))
    answer = assistant.ask("capital of France")
    context = build_context(answer.sources)
    assert context.startswith("[1] a.pdf, page 1")
    messages = build_messages("q", answer.sources, [])
    assert "ONLY" in messages[0]["content"]
    assert messages[-1]["content"].endswith("Question: q")
