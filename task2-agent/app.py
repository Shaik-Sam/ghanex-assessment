import json
import os

import streamlit as st
from dotenv import load_dotenv

from agent import ToolCallingAgent, build_default_registry
from agent.config import get_settings
from agent.tools import HttpClient

load_dotenv()

st.set_page_config(page_title="Tool-Calling AI Agent", page_icon="🤖", layout="centered")

EXAMPLES = [
    "Hi there! What can you do?",
    "What is 18% of 2450 plus the square root of 144?",
    "What's the weather in Hyderabad right now?",
    "Convert 250 USD to INR",
    "Who was Ada Lovelace?",
    "Compare the weather in London and Tokyo, then tell me which is warmer",
]


def resolve_api_key() -> str | None:
    try:
        secret = st.secrets.get("GROQ_API_KEY")
    except Exception:
        secret = None
    return secret or os.getenv("GROQ_API_KEY")


def get_agent() -> ToolCallingAgent | None:
    if "agent" in st.session_state:
        return st.session_state.agent
    api_key = resolve_api_key()
    if not api_key:
        return None
    settings = get_settings()
    registry = build_default_registry(HttpClient(settings.http_timeout))
    agent = ToolCallingAgent(registry, settings, api_key=api_key)
    st.session_state.agent = agent
    return agent


def render_events(events):
    for event in events:
        icon = "⚠️" if event["failed"] else "🔧"
        with st.expander(f"{icon} {event['name']}"):
            st.caption("Arguments")
            st.code(json.dumps(event["arguments"], indent=2, default=str), language="json")
            st.caption("Result")
            st.code(json.dumps(event["result"], indent=2, default=str), language="json")


def handle(agent: ToolCallingAgent, prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt, "events": []})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = agent.run(prompt)
        events = [{"name": e.name, "arguments": e.arguments, "result": e.result, "failed": e.failed} for e in reply.tool_events]
        render_events(events)
        if reply.error:
            st.warning(reply.text)
        else:
            st.markdown(reply.text)
    st.session_state.messages.append({"role": "assistant", "content": reply.text, "events": events})


def main():
    st.title("🤖 Tool-Calling AI Agent")
    st.caption("Chat naturally. The agent decides when to use its calculator, weather, Wikipedia and currency tools.")

    agent = get_agent()
    if agent is None:
        st.warning("No GROQ_API_KEY found. Set it as an environment variable or in Streamlit secrets, then reload.")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.sidebar:
        st.header("Tools")
        for name in agent.registry.names():
            st.write(f"• `{name}`")
        st.header("Try asking")
        for index, example in enumerate(EXAMPLES):
            if st.button(example, key=f"example-{index}", use_container_width=True):
                st.session_state.pending = example
        if st.button("Clear conversation", type="secondary"):
            agent.reset()
            st.session_state.messages = []
            st.rerun()
        st.caption(f"Model: {agent.settings.model}")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_events(message["events"])
            st.markdown(message["content"])

    pending = st.session_state.pop("pending", None)
    prompt = st.chat_input("Message the agent") or pending
    if prompt:
        handle(agent, prompt)


main()
