import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    max_steps: int = 5
    max_history_messages: int = 20
    http_timeout: float = 10.0
    temperature: float = 0.2


def get_settings() -> Settings:
    return Settings()
