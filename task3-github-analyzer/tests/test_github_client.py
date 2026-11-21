import requests
import pytest

from analyzer.errors import EmptyRepositoryError, GitHubAPIError, RateLimitError, RepositoryNotFoundError
from analyzer.github_client import GitHubClient
from analyzer.models import RepoRef
from tests.conftest import FakeResponse, FakeSession, REPO, default_routes

REF = RepoRef("acme", "demo")


def test_fetch_collects_all_data(session):
    data = GitHubClient(session=session).fetch(REF)
    assert data.ref.full_name == "acme/demo"
    assert data.languages == {"Python": 900, "Shell": 100}
    assert "Hello" in data.readme
    assert "src/app.py" in data.tree_paths
    assert data.descriptors == {"requirements.txt": "requests==2.0"}
    assert [i["number"] for i in data.good_first_issues] == [1]


def test_token_is_sent_as_bearer(session):
    client = GitHubClient(token="abc", session=session)
    assert session.headers["Authorization"] == "Bearer abc"
    assert client.authenticated


def test_missing_repository_raises_not_found():
    client = GitHubClient(session=FakeSession({}))
    with pytest.raises(RepositoryNotFoundError):
        client.fetch(REF)


def test_rate_limit_detected_from_headers():
    routes = {"/repos/acme/demo": FakeResponse({"message": "x"}, 403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1800000000"})}
    with pytest.raises(RateLimitError) as info:
        GitHubClient(session=FakeSession(routes)).fetch(REF)
    assert info.value.reset_at == 1800000000
    assert "token" in str(info.value)


def test_rate_limit_detected_from_message_and_429():
    routes = {"/repos/acme/demo": FakeResponse({"message": "API rate limit exceeded"}, 403)}
    with pytest.raises(RateLimitError):
        GitHubClient(session=FakeSession(routes)).fetch(REF)
    routes = {"/repos/acme/demo": FakeResponse({}, 429)}
    with pytest.raises(RateLimitError):
        GitHubClient(token="t", session=FakeSession(routes)).fetch(REF)


def test_forbidden_without_rate_limit_is_api_error():
    routes = {"/repos/acme/demo": FakeResponse({"message": "Resource not accessible"}, 403, {"X-RateLimit-Remaining": "50"})}
    with pytest.raises(GitHubAPIError):
        GitHubClient(session=FakeSession(routes)).fetch(REF)


def test_bad_token_message():
    routes = {"/repos/acme/demo": FakeResponse({}, 401)}
    with pytest.raises(GitHubAPIError, match="token"):
        GitHubClient(token="bad", session=FakeSession(routes)).fetch(REF)


@pytest.mark.parametrize("error,fragment", [(requests.Timeout(), "in time"), (requests.ConnectionError(), "connect")])
def test_network_errors(error, fragment):
    with pytest.raises(GitHubAPIError, match=fragment):
        GitHubClient(session=FakeSession({"/repos/acme/demo": error})).fetch(REF)


def test_empty_repository():
    routes = {"/repos/acme/demo": FakeResponse({**REPO, "size": 0}), "/git/trees/main": FakeResponse(status=409)}
    with pytest.raises(EmptyRepositoryError):
        GitHubClient(session=FakeSession(routes)).fetch(REF)


def test_missing_readme_and_languages_are_tolerated():
    routes = default_routes()
    del routes["/repos/acme/demo/readme"]
    del routes["/repos/acme/demo/languages"]
    data = GitHubClient(session=FakeSession(routes)).fetch(REF)
    assert data.readme == ""
    assert data.languages == {}


def test_unreadable_json_is_reported():
    routes = {"/repos/acme/demo": FakeResponse(None)}
    with pytest.raises(GitHubAPIError, match="unreadable"):
        GitHubClient(session=FakeSession(routes)).fetch(REF)


def test_bad_token_raises_authentication_error():
    from analyzer.errors import AuthenticationError

    routes = {"/repos/acme/demo": FakeResponse({}, 401)}
    with pytest.raises(AuthenticationError):
        GitHubClient(token="bad", session=FakeSession(routes)).fetch(REF)
