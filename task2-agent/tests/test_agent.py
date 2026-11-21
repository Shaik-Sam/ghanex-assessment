import json

import pytest

from agent.config import Settings
from agent.core import ToolCallingAgent
from agent.tools import build_default_registry
from tests.conftest import FakeResponse, ScriptedClient, llm_message, tool_call

SETTINGS = Settings(max_steps=3)


class RateLimitError(Exception):
    pass


class APIConnectionError(Exception):
    pass


@pytest.fixture
def registry(http_factory):
    return build_default_registry(
        http_factory(
            {
                "frankfurter": FakeResponse({"rates": {"INR": 80.0}, "date": "d"}),
                "geocoding": FakeResponse({}),
            }
        )
    )


def make_agent(registry, script):
    client = ScriptedClient(script)
    return ToolCallingAgent(registry, SETTINGS, client=client), client


def test_direct_answer_makes_no_tool_call(registry):
    agent, client = make_agent(registry, [llm_message("Hello! How can I help?")])
    reply = agent.run("hi")
    assert reply.text == "Hello! How can I help?"
    assert reply.tool_events == []
    assert not reply.error
    assert len(client.requests) == 1
    assert client.requests[0]["tools"]


def test_single_tool_call_is_executed_and_synthesised(registry):
    script = [
        llm_message(tool_calls=[tool_call("calculator", {"expression": "2+3*4"})]),
        llm_message("The answer is 14."),
    ]
    agent, client = make_agent(registry, script)
    reply = agent.run("what is 2+3*4")
    assert reply.text == "The answer is 14."
    assert reply.tool_events[0].result["result"] == 14
    tool_message = client.requests[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert json.loads(tool_message["content"])["result"] == 14


def test_multiple_sequential_tools(registry):
    script = [
        llm_message(tool_calls=[tool_call("convert_currency", {"amount": 10, "from_currency": "USD", "to_currency": "INR"}, "a")]),
        llm_message(tool_calls=[tool_call("calculator", {"expression": "800 * 2"}, "b")]),
        llm_message("Done."),
    ]
    agent, _ = make_agent(registry, script)
    reply = agent.run("convert then double")
    assert [e.name for e in reply.tool_events] == ["convert_currency", "calculator"]
    assert reply.tool_events[1].result["result"] == 1600


def test_parallel_tool_calls_in_one_step(registry):
    script = [
        llm_message(tool_calls=[tool_call("calculator", {"expression": "1+1"}, "a"), tool_call("calculator", {"expression": "2+2"}, "b")]),
        llm_message("2 and 4."),
    ]
    agent, client = make_agent(registry, script)
    reply = agent.run("two sums")
    assert len(reply.tool_events) == 2
    roles = [m["role"] for m in client.requests[1]["messages"]]
    assert roles.count("tool") == 2


def test_tool_failure_is_passed_back_to_model_without_crashing(registry):
    script = [
        llm_message(tool_calls=[tool_call("get_weather", {"location": "Atlantis"})]),
        llm_message("I couldn't find Atlantis."),
    ]
    agent, client = make_agent(registry, script)
    reply = agent.run("weather in Atlantis")
    assert reply.tool_events[0].failed
    assert reply.text == "I couldn't find Atlantis."
    assert "error" in json.loads(client.requests[1]["messages"][-1]["content"])


def test_malformed_tool_arguments_are_handled(registry):
    script = [
        llm_message(tool_calls=[tool_call("calculator", "{not json")]),
        llm_message("Sorry, let me retry."),
    ]
    agent, _ = make_agent(registry, script)
    reply = agent.run("calc")
    assert reply.tool_events[0].failed
    assert not reply.error


def test_unknown_tool_is_handled(registry):
    script = [llm_message(tool_calls=[tool_call("launch_rocket", {})]), llm_message("I can't do that.")]
    agent, _ = make_agent(registry, script)
    reply = agent.run("launch")
    assert "Unknown tool" in reply.tool_events[0].result["error"]


def test_history_is_kept_across_turns(registry):
    script = [llm_message("Nice to meet you, Sam."), llm_message("Your name is Sam.")]
    agent, client = make_agent(registry, script)
    agent.run("my name is Sam")
    agent.run("what is my name?")
    contents = [m["content"] for m in client.requests[1]["messages"] if m["role"] != "system"]
    assert "my name is Sam" in contents
    assert "Nice to meet you, Sam." in contents


def test_infinite_tool_loop_is_stopped(registry):
    looping = [llm_message(tool_calls=[tool_call("calculator", {"expression": "1+1"}, f"c{i}")]) for i in range(10)]
    agent, client = make_agent(registry, looping + [llm_message("wrap up")])
    reply = agent.run("loop")
    assert len(client.requests) <= SETTINGS.max_steps + 1
    assert "tools" not in client.requests[-1]
    assert reply.text


@pytest.mark.parametrize(
    "exc,fragment",
    [
        (RateLimitError("x"), "rate limit"),
        (APIConnectionError("x"), "could not reach"),
        (RuntimeError("boom"), "problem"),
    ],
)
def test_llm_errors_become_friendly_messages_and_roll_back_history(registry, exc, fragment):
    agent, _ = make_agent(registry, [exc])
    reply = agent.run("hello")
    assert reply.error
    assert fragment in reply.text.lower()
    assert agent.history == []


def test_blank_message_rejected(registry):
    agent, client = make_agent(registry, [])
    assert agent.run("   ").error
    assert client.requests == []


def test_reset_clears_history(registry):
    agent, _ = make_agent(registry, [llm_message("hi")])
    agent.run("hello")
    agent.reset()
    assert agent.history == []


def test_history_window_never_starts_mid_tool_exchange(registry):
    agent = ToolCallingAgent(registry, Settings(max_history_messages=3), client=ScriptedClient([]))
    agent.history = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "", "tool_calls": []},
        {"role": "tool", "tool_call_id": "x", "content": "{}"},
        {"role": "assistant", "content": "a1"},
    ]
    assert agent._trim_history() == []


class NotFoundError(Exception):
    pass


def test_retired_model_gives_actionable_message(registry):
    agent, _ = make_agent(registry, [NotFoundError("404")])
    reply = agent.run("hello")
    assert reply.error
    assert "GROQ_MODEL" in reply.text
