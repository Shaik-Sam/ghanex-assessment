import base64
import json

import pytest
import requests


class FakeResponse:
    def __init__(self, payload=None, status=200, headers=None):
        self.payload = payload
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        if self.payload is None:
            raise ValueError("no json")
        return self.payload


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        best = None
        for fragment, outcome in self.routes.items():
            if url.endswith(fragment) and (best is None or len(fragment) > len(best)):
                best = fragment
        if best is None:
            return FakeResponse(status=404)
        outcome = self.routes[best]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def b64(text):
    return {"encoding": "base64", "content": base64.b64encode(text.encode()).decode()}


REPO = {
    "name": "demo",
    "owner": {"login": "acme"},
    "description": "A demo project",
    "language": "Python",
    "stargazers_count": 120,
    "forks_count": 10,
    "open_issues_count": 4,
    "license": {"spdx_id": "MIT"},
    "topics": ["demo"],
    "default_branch": "main",
    "size": 100,
    "html_url": "https://github.com/acme/demo",
}

TREE = {
    "tree": [
        {"path": "README.md", "type": "blob"},
        {"path": "LICENSE", "type": "blob"},
        {"path": "requirements.txt", "type": "blob"},
        {"path": "src", "type": "tree"},
        {"path": "src/app.py", "type": "blob"},
        {"path": "tests", "type": "tree"},
        {"path": "tests/test_app.py", "type": "blob"},
        {"path": ".github/workflows/ci.yml", "type": "blob"},
    ],
    "truncated": False,
}

ANALYSIS_JSON = {
    "executive_summary": "A small Python demo project.",
    "tech_stack": ["Python"],
    "strengths": ["Has tests", "Has CI", "MIT licensed"],
    "architecture_patterns": ["src layout"],
    "code_organization": "Source in src, tests in tests.",
    "recommendations": [
        {"title": "Add coverage", "detail": "Track coverage in CI.", "priority": "high", "category": "testing"},
        {"title": "Add docs", "detail": "Create a docs folder.", "priority": "medium", "category": "documentation"},
        {"title": "Add linting", "detail": "Use ruff.", "priority": "low", "category": "tooling"},
    ],
    "contribution_opportunities": ["Expand tests", "Improve README"],
}


def default_routes():
    return {
        "/repos/acme/demo": FakeResponse(REPO),
        "/repos/acme/demo/languages": FakeResponse({"Python": 900, "Shell": 100}),
        "/repos/acme/demo/readme": FakeResponse(b64("# Demo\nHello")),
        "/git/trees/main": FakeResponse(TREE),
        "/contents/requirements.txt": FakeResponse(b64("requests==2.0")),
        "/repos/acme/demo/issues": FakeResponse(
            [
                {"number": 1, "title": "Fix typo", "html_url": "https://github.com/acme/demo/issues/1", "comments": 0},
                {"number": 2, "title": "A PR", "html_url": "u", "comments": 0, "pull_request": {}},
            ]
        ),
    }


class FakeLLMClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []
        from types import SimpleNamespace

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        from types import SimpleNamespace

        self.calls.append(kwargs)
        item = self.outputs.pop(0)
        if isinstance(item, Exception):
            raise item
        if not isinstance(item, str):
            item = json.dumps(item)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=item))])


@pytest.fixture
def session():
    return FakeSession(default_routes())
