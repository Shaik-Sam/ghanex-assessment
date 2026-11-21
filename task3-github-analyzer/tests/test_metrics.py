from analyzer.metrics import compute_metrics, health_score, language_percentages
from tests.conftest import TREE


def paths():
    return [item["path"] for item in TREE["tree"]]


def test_detects_project_features():
    metrics = compute_metrics(paths())
    assert metrics.has_tests
    assert metrics.has_ci
    assert metrics.has_license
    assert not metrics.has_docker
    assert metrics.total_files == 6
    assert metrics.total_dirs == 4
    assert ".py" in metrics.extension_counts
    assert "src" in metrics.top_level_dirs


def test_detects_misc_files():
    metrics = compute_metrics(
        ["Dockerfile", "CHANGELOG.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "docs/index.md", "ruff.toml", "mypy.ini", ".gitignore"]
    )
    assert metrics.has_docker and metrics.has_changelog and metrics.has_contributing
    assert metrics.has_code_of_conduct and metrics.has_docs_dir and metrics.has_linter_config
    assert metrics.has_type_config and metrics.has_gitignore


def test_contributing_in_dot_github():
    assert compute_metrics([".github/CONTRIBUTING.md"]).has_contributing


def test_empty_tree_scores_only_from_flags():
    metrics = compute_metrics([])
    score, breakdown = health_score(metrics, has_readme=False, has_description=False)
    assert score == 0
    assert not any(breakdown.values())


def test_health_score_range():
    metrics = compute_metrics(paths())
    score, breakdown = health_score(metrics, has_readme=True, has_description=True)
    assert 0 < score < 100
    assert breakdown["README"] and breakdown["Tests"]


def test_language_percentages():
    assert language_percentages({"Python": 900, "Shell": 100}) == {"Python": 90.0, "Shell": 10.0}
    assert language_percentages({}) == {}
