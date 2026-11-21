import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 4
    min_score: float = 0.25
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    llm_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    max_history_turns: int = 4
    max_upload_mb: int = 25


def get_settings() -> Settings:
    return Settings()
