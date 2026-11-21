import json
import os
from dataclasses import dataclass, field
from typing import Any

from agent.config import Settings
from agent.registry import ToolRegistry

SYSTEM_PROMPT = (
    "You are a friendly, concise assistant with access to tools. "
    "Decide for each message whether a tool is needed. "
    "Reply directly, without tools, to greetings, small talk, opinions and general knowledge you are confident about. "
    "Use calculator for any arithmetic, get_weather for weather, convert_currency for money conversion "
    "and search_wikipedia for factual lookups that benefit from a reference source. "
    "You may call several tools, one after another, when a question needs it. "
    "Never invent tool results. If a tool returns an error, explain the problem simply, "
    "suggest what the user can try, and do not pretend it succeeded. "
    "Use the earlier conversation to resolve references such as 'there' or 'that amount'."
)

FALLBACK_REPLY = "I ran into a problem while working on that. Please try again or rephrase your request."


@dataclass
class ToolEvent:
    name: str
    arguments: dict[str, Any] | str
    result: dict[str, Any]

    @property
    def failed(self) -> bool:
        return "error" in self.result


@dataclass
class AgentReply:
    text: str
    tool_events: list[ToolEvent] = field(default_factory=list)
    error: bool = False


class ToolCallingAgent:
    def __init__(self, registry: ToolRegistry, settings: Settings, client: Any = None, api_key: str | None = None):
        self.registry = registry
        self.settings = settings
        self.history: list[dict[str, Any]] = []
        if client is not None:
            self._client = client
        else:
            key = api_key or os.getenv("GROQ_API_KEY")
            if not key:
                raise ValueError("GROQ_API_KEY is not set.")
            from groq import Groq

            self._client = Groq(api_key=key)

    def reset(self) -> None:
        self.history.clear()

    def _trim_history(self) -> list[dict[str, Any]]:
        limit = self.settings.max_history_messages
        window = self.history[-limit:]
        while window and window[0]["role"] != "user":
            window = window[1:]
        return window

    def _complete(self, messages: list[dict[str, Any]], allow_tools: bool):
        kwargs: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
            "max_tokens": 2048,
        }
        if allow_tools:
            kwargs["tools"] = self.registry.schemas()
            kwargs["tool_choice"] = "auto"
        return self._client.chat.completions.create(**kwargs)

    def _friendly_error(self, exc: Exception) -> str:
        names = {cls.__name__ for cls in type(exc).__mro__}
        if "RateLimitError" in names:
            return "The language model rate limit was reached. Please wait a moment and try again."
        if "APIConnectionError" in names:
            return "I could not reach the language model service. Please check the connection and try again."
        if "AuthenticationError" in names:
            return "The language model API key was rejected. Please check GROQ_API_KEY."
        if "NotFoundError" in names:
            return f"The model '{self.settings.model}' is not available on your Groq account. Set GROQ_MODEL to a supported model such as openai/gpt-oss-120b."
        if "BadRequestError" in names:
            return "The language model could not process that request. Try rephrasing it."
        if "APIStatusError" in names:
            return "The language model service reported an error. Please try again shortly."
        return FALLBACK_REPLY

    def run(self, user_message: str) -> AgentReply:
        user_message = user_message.strip()
        if not user_message:
            return AgentReply(text="Please type a message.", error=True)

        checkpoint = len(self.history)
        self.history.append({"role": "user", "content": user_message})
        events: list[ToolEvent] = []
        turn: list[dict[str, Any]] = []

        try:
            for step in range(self.settings.max_steps + 1):
                allow_tools = step < self.settings.max_steps
                messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self._trim_history(), *turn]
                response = self._complete(messages, allow_tools)
                message = response.choices[0].message
                calls = list(message.tool_calls or []) if allow_tools else []

                if not calls:
                    text = (message.content or "").strip() or FALLBACK_REPLY
                    self.history.extend(turn)
                    self.history.append({"role": "assistant", "content": text})
                    return AgentReply(text=text, tool_events=events)

                turn.append(
                    {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {"name": call.function.name, "arguments": call.function.arguments or "{}"},
                            }
                            for call in calls
                        ],
                    }
                )
                for call in calls:
                    raw = call.function.arguments
                    result = self.registry.execute(call.function.name, raw)
                    try:
                        parsed = json.loads(raw) if raw else {}
                    except json.JSONDecodeError:
                        parsed = raw
                    events.append(ToolEvent(name=call.function.name, arguments=parsed, result=result))
                    turn.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(result, default=str),
                        }
                    )
        except Exception as exc:
            del self.history[checkpoint:]
            return AgentReply(text=self._friendly_error(exc), tool_events=events, error=True)

        del self.history[checkpoint:]
        return AgentReply(text=FALLBACK_REPLY, tool_events=events, error=True)
