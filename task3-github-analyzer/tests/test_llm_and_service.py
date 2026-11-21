import json

import pytest

from analyzer.errors import InvalidRepositoryError, LLMError
from analyzer.github_client import GitHubClient
from analyzer.llm import GroqAnalyzer, build_prompt, extract_json, parse_analysis
from analyzer.metrics import compute_metrics
from analyzer.service import RepositoryAnalyzer
from tests.conftest import ANALYSIS_JSON, FakeLLMClient


class RateLimitError(Exception):
    pass


def data_and_metrics(session):
    data = GitHubClient(session=session).fetch(__import__("analyzer.models", fromlist=["RepoRef"]).RepoRef("acme", "demo"))
    return data, compute_metrics(data.tree_paths)


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Here you go: {"a": 1} thanks') == {"a": 1}
    with pytest.raises(LLMError):
        extract_json("no json here")
    with pytest.raises(LLMError):
        extract_json("{broken")
    with pytest.raises(LLMError):
        extract_json("[1, 2]")


def test_parse_analysis_normalises_values():
    payload = dict(ANALYSIS_JSON)
    payload["recommendations"] = [
        {"title": "t1", "detail": "d1", "priority": "URGENT", "category": "CI-CD"},
        {"title": "t2", "detail": "d2", "priority": "High", "category": "bogus"},
        {"title": "t3", "detail": "d3"},
        {"title": "", "detail": "ignored"},
        "not a dict",
    ]
    analysis = parse_analysis(payload)
    assert [r.priority for r in analysis.recommendations] == ["medium", "high", "medium"]
    assert [r.category for r in analysis.recommendations] == ["ci_cd", "tooling", "tooling"]


def test_requires_three_recommendations_and_summary():
    payload = dict(ANALYSIS_JSON, recommendations=ANALYSIS_JSON["recommendations"][:2])
    with pytest.raises(LLMError, match="three"):
        parse_analysis(payload)
    with pytest.raises(LLMError, match="summary"):
        parse_analysis(dict(ANALYSIS_JSON, executive_summary=" "))


def test_prompt_contains_key_facts(session):
    data, metrics = data_and_metrics(session)
    prompt = build_prompt(data, metrics)
    for expected in ("acme/demo", "src/app.py", "requests==2.0", "Fix typo", "# Demo", "MIT"):
        assert expected in prompt


def test_analyzer_retries_on_bad_output_then_succeeds(session):
    data, metrics = data_and_metrics(session)
    client = FakeLLMClient(["not json", ANALYSIS_JSON])
    analysis = GroqAnalyzer(client=client).analyze(data, metrics)
    assert len(client.calls) == 2
    assert len(analysis.recommendations) == 3
    assert client.calls[0]["response_format"] == {"type": "json_object"}


def test_analyzer_fails_after_retries(session):
    data, metrics = data_and_metrics(session)
    with pytest.raises(LLMError):
        GroqAnalyzer(client=FakeLLMClient(["x", "y"])).analyze(data, metrics)


def test_rate_limit_is_not_retried(session):
    data, metrics = data_and_metrics(session)
    client = FakeLLMClient([RateLimitError("slow down"), ANALYSIS_JSON])
    with pytest.raises(LLMError, match="rate limit"):
        GroqAnalyzer(client=client).analyze(data, metrics)
    assert len(client.calls) == 1


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LLMError, match="GROQ_API_KEY"):
        GroqAnalyzer()


def test_end_to_end_report(session):
    service = RepositoryAnalyzer(GitHubClient(session=session), GroqAnalyzer(client=FakeLLMClient([json.dumps(ANALYSIS_JSON)])))
    report = service.run("https://github.com/acme/demo")
    assert report.data.ref.full_name == "acme/demo"
    assert report.metrics.has_ci
    assert report.health_score == 50
    assert report.analysis.executive_summary


def test_invalid_input_rejected_before_any_request(session):
    service = RepositoryAnalyzer(GitHubClient(session=session), GroqAnalyzer(client=FakeLLMClient([])))
    with pytest.raises(InvalidRepositoryError):
        service.run("not a repo")
    assert session.calls == []
