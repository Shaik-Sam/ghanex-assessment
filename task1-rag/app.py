import os

import streamlit as st
from dotenv import load_dotenv

from rag import DocumentAssistant
from rag.config import get_settings
from rag.embedder import FastEmbedder
from rag.errors import RagError
from rag.generator import GroqGenerator

load_dotenv()

st.set_page_config(page_title="PDF Document Assistant", page_icon="📄", layout="wide")


def resolve_api_key() -> str | None:
    try:
        secret = st.secrets.get("GROQ_API_KEY")
    except Exception:
        secret = None
    return secret or os.getenv("GROQ_API_KEY")


@st.cache_resource(show_spinner="Loading embedding model...")
def load_embedder(model_name: str) -> FastEmbedder:
    return FastEmbedder(model_name)


def get_assistant() -> DocumentAssistant | None:
    if "assistant" in st.session_state:
        return st.session_state.assistant
    settings = get_settings()
    api_key = resolve_api_key()
    if not api_key:
        return None
    try:
        generator = GroqGenerator(settings.llm_model, api_key)
    except RagError as exc:
        st.error(str(exc))
        return None
    assistant = DocumentAssistant(load_embedder(settings.embedding_model), generator, settings)
    st.session_state.assistant = assistant
    return assistant


def render_sources(sources):
    for number, source in enumerate(sources, start=1):
        label = f"[{number}] {source.document} · page {source.page} · chunk {source.chunk_index} · similarity {source.score:.2f}"
        with st.expander(label):
            st.write(source.text)


def render_sidebar(assistant: DocumentAssistant):
    settings = get_settings()
    with st.sidebar:
        st.header("Documents")
        uploads = st.file_uploader(
            "Upload PDF files",
            type=["pdf"],
            accept_multiple_files=True,
            help=f"Up to {settings.max_upload_mb} MB per file.",
        )
        if st.button("Process documents", type="primary", disabled=not uploads):
            with st.spinner("Extracting, chunking and embedding..."):
                for upload in uploads:
                    result = assistant.ingest(upload.name, upload.getvalue())
                    if result.error:
                        st.error(result.error)
                    elif result.skipped:
                        st.info(f"'{result.document}' is already indexed.")
                    else:
                        st.success(
                            f"'{result.document}': {result.pages} pages, {result.chunks} chunks indexed."
                        )

        if assistant.documents:
            st.subheader("Indexed")
            for name in list(assistant.documents):
                left, right = st.columns([4, 1])
                left.write(name)
                if right.button("✕", key=f"remove-{name}", help=f"Remove {name}"):
                    assistant.remove(name)
                    st.rerun()
            if st.button("Clear everything"):
                assistant.reset()
                st.session_state.messages = []
                st.rerun()

        st.divider()
        st.caption(
            f"Embeddings: {settings.embedding_model}  \n"
            f"LLM: {settings.llm_model}  \n"
            f"Chunk size {settings.chunk_size}, overlap {settings.chunk_overlap}, top-k {settings.top_k}"
        )


def main():
    st.title("📄 PDF Document Assistant")
    st.caption("Ask questions about your PDFs. Answers are grounded in the uploaded text and cite their sources.")

    assistant = get_assistant()
    if assistant is None:
        st.warning(
            "No GROQ_API_KEY found. Set it as an environment variable or in Streamlit secrets, then reload."
        )
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    render_sidebar(assistant)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                render_sources(message["sources"])

    question = st.chat_input("Ask a question about your documents")
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching documents..."):
                answer = assistant.ask(question)
        except RagError as exc:
            st.warning(str(exc))
            st.session_state.messages.append({"role": "assistant", "content": str(exc)})
            return
        except Exception:
            message = "Something unexpected went wrong while answering. Please try again."
            st.error(message)
            st.session_state.messages.append({"role": "assistant", "content": message})
            return
        st.markdown(answer.text)
        if answer.sources:
            render_sources(answer.sources)
        st.session_state.messages.append(
            {"role": "assistant", "content": answer.text, "sources": answer.sources}
        )


main()
