import os

from rag.errors import GenerationError
from rag.models import Source

SYSTEM_PROMPT = (
    "You are a document question-answering assistant. "
    "Answer the user's question using ONLY the numbered context passages provided. "
    "Do not use outside knowledge and do not guess. "
    "If the passages do not contain the answer, reply exactly: "
    "\"I could not find the answer to that in the uploaded documents.\" "
    "When you use a passage, cite it inline with its number in square brackets, such as [1] or [2][3]. "
    "Keep answers concise and accurate."
)

NOT_FOUND_MESSAGE = "I could not find the answer to that in the uploaded documents."


def build_context(sources: list[Source]) -> str:
    blocks = []
    for number, source in enumerate(sources, start=1):
        header = f"[{number}] {source.document}, page {source.page}"
        blocks.append(f"{header}\n{source.text}")
    return "\n\n".join(blocks)


def build_messages(
    question: str, sources: list[Source], history: list[dict[str, str]]
) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    user_content = f"Context passages:\n\n{build_context(sources)}\n\nQuestion: {question}"
    messages.append({"role": "user", "content": user_content})
    return messages


class GroqGenerator:
    def __init__(self, model: str, api_key: str | None = None):
        self.model = model
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise GenerationError(
                "GROQ_API_KEY is not set. Add it to your environment or Streamlit secrets."
            )
        from groq import Groq

        self._client = Groq(api_key=self.api_key)

    def generate(
        self, question: str, sources: list[Source], history: list[dict[str, str]]
    ) -> str:
        from groq import APIConnectionError, APIStatusError, RateLimitError

        messages = build_messages(question, sources, history)
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
            )
        except RateLimitError as exc:
            raise GenerationError(
                "The language model rate limit was reached. Wait a moment and try again."
            ) from exc
        except APIConnectionError as exc:
            raise GenerationError(
                "Could not reach the language model service. Check your connection."
            ) from exc
        except APIStatusError as exc:
            if exc.status_code == 404:
                raise GenerationError(
                    f"The model '{self.model}' is not available on your Groq account. "
                    "Set GROQ_MODEL to a currently supported model such as openai/gpt-oss-120b."
                ) from exc
            raise GenerationError(
                f"The language model returned an error (status {exc.status_code})."
            ) from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise GenerationError("The language model returned an empty response.")
        return content.strip()
