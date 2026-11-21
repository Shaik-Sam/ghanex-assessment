import pytest

from analyzer.errors import InvalidRepositoryError
from analyzer.parsing import parse_repo_reference


@pytest.mark.parametrize(
    "value",
    [
        "pallets/flask",
        "https://github.com/pallets/flask",
        "http://github.com/pallets/flask/",
        "github.com/pallets/flask",
        "www.github.com/pallets/flask",
        "https://github.com/pallets/flask.git",
        "git@github.com:pallets/flask.git",
        "https://github.com/pallets/flask/tree/main/src",
        "https://github.com/pallets/flask/issues/12?x=1#top",
        "  pallets/flask  ",
    ],
)
def test_valid_references(value):
    ref = parse_repo_reference(value)
    assert (ref.owner, ref.name) == ("pallets", "flask")


def test_dotted_repo_names_are_kept():
    assert parse_repo_reference("vercel/next.js").name == "next.js"


@pytest.mark.parametrize(
    "value",
    ["", "   ", "flask", "https://gitlab.com/a/b", "https://github.com/", "https://github.com/orgs/x", "-bad/repo", "own er/repo", "a/b c", "a/.."],
)
def test_invalid_references(value):
    with pytest.raises(InvalidRepositoryError):
        parse_repo_reference(value)
