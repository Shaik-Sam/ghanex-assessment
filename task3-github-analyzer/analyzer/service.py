from typing import Protocol

from analyzer.github_client import GitHubClient
from analyzer.metrics import compute_metrics, health_score
from analyzer.models import Analysis, Report, RepoData, StructureMetrics
from analyzer.parsing import parse_repo_reference


class Analyst(Protocol):
    def analyze(self, data: RepoData, metrics: StructureMetrics) -> Analysis: ...


class RepositoryAnalyzer:
    def __init__(self, github: GitHubClient, analyst: Analyst):
        self.github = github
        self.analyst = analyst

    def run(self, reference: str) -> Report:
        ref = parse_repo_reference(reference)
        data = self.github.fetch(ref)
        metrics = compute_metrics(data.tree_paths)
        score, breakdown = health_score(
            metrics,
            has_readme=bool(data.readme.strip()),
            has_description=bool(data.metadata.get("description")),
        )
        analysis = self.analyst.analyze(data, metrics)
        return Report(data=data, metrics=metrics, health_score=score, health_breakdown=breakdown, analysis=analysis)
