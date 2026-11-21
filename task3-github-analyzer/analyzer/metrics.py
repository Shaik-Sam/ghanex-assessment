import posixpath
from collections import Counter

from analyzer.models import StructureMetrics

TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "testing"}
DOC_DIRS = {"docs", "doc", "documentation"}
LINTER_FILES = {
    ".flake8", ".pylintrc", "ruff.toml", ".ruff.toml", ".eslintrc", ".eslintrc.js",
    ".eslintrc.json", ".eslintrc.cjs", "eslint.config.js", "eslint.config.mjs",
    ".prettierrc", ".golangci.yml", ".golangci.yaml", "rustfmt.toml", ".pre-commit-config.yaml",
}
TYPE_FILES = {"mypy.ini", "tsconfig.json", "pyrightconfig.json", ".mypy.ini"}
IGNORED_EXTENSIONS = {"", ".lock", ".sum"}

HEALTH_CHECKS = {
    "License": "has_license",
    "Tests": "has_tests",
    "CI workflow": "has_ci",
    "Documentation folder": "has_docs_dir",
    "Contributing guide": "has_contributing",
    "Linter / formatter config": "has_linter_config",
    "Changelog": "has_changelog",
    "Code of conduct": "has_code_of_conduct",
}


def compute_metrics(paths: list[str]) -> StructureMetrics:
    metrics = StructureMetrics()
    extensions: Counter[str] = Counter()
    top_dirs: set[str] = set()
    directories = set()

    for path in paths:
        parts = path.split("/")
        metrics.max_depth = max(metrics.max_depth, len(parts))
        for depth in range(1, len(parts)):
            directories.add("/".join(parts[:depth]))
        if len(parts) > 1:
            top_dirs.add(parts[0])

    file_paths = [p for p in paths if p not in directories]
    metrics.total_files = len(file_paths)
    metrics.total_dirs = len(directories)
    metrics.top_level_dirs = sorted(top_dirs)

    lowered_dirs = {part.lower() for path in paths for part in path.split("/")[:-1]}
    lowered_top = {d.lower() for d in top_dirs}

    for path in file_paths:
        name = posixpath.basename(path)
        lower_name = name.lower()
        extension = posixpath.splitext(lower_name)[1]
        if extension not in IGNORED_EXTENSIONS:
            extensions[extension] += 1

        stem = lower_name.split(".")[0]
        if stem in {"license", "licence", "copying", "unlicense"}:
            metrics.has_license = True
        if stem == "contributing" and "/" not in path or path.lower().endswith("/contributing.md"):
            metrics.has_contributing = True
        if stem == "code_of_conduct":
            metrics.has_code_of_conduct = True
        if stem in {"changelog", "changes", "history", "news", "releases"} and "/" not in path:
            metrics.has_changelog = True
        if lower_name == ".gitignore":
            metrics.has_gitignore = True
        if lower_name in LINTER_FILES:
            metrics.has_linter_config = True
        if lower_name in TYPE_FILES:
            metrics.has_type_config = True
        if lower_name in {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml"} or lower_name.startswith("dockerfile."):
            metrics.has_docker = True
        if path.startswith(".github/workflows/") and extension in {".yml", ".yaml"}:
            metrics.has_ci = True
        if lower_name in {".travis.yml", ".gitlab-ci.yml", "azure-pipelines.yml", "jenkinsfile", ".drone.yml"}:
            metrics.has_ci = True
        if path.startswith(".circleci/"):
            metrics.has_ci = True
        if (stem.startswith("test_") or stem.endswith("_test") or ".test." in lower_name or ".spec." in lower_name):
            metrics.has_tests = True

    if lowered_dirs & TEST_DIRS:
        metrics.has_tests = True
    if lowered_top & DOC_DIRS:
        metrics.has_docs_dir = True
    metrics.extension_counts = dict(extensions.most_common(10))
    return metrics


def health_score(metrics: StructureMetrics, has_readme: bool, has_description: bool) -> tuple[int, dict[str, bool]]:
    breakdown = {label: bool(getattr(metrics, attribute)) for label, attribute in HEALTH_CHECKS.items()}
    breakdown["README"] = has_readme
    breakdown["Repository description"] = has_description
    score = round(100 * sum(breakdown.values()) / len(breakdown))
    return score, breakdown


def language_percentages(languages: dict[str, int]) -> dict[str, float]:
    total = sum(languages.values())
    if not total:
        return {}
    return {
        name: round(100 * size / total, 1)
        for name, size in sorted(languages.items(), key=lambda item: item[1], reverse=True)
    }
