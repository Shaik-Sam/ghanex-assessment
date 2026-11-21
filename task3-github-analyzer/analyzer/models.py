from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RepoRef:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass
class RepoData:
    ref: RepoRef
    metadata: dict[str, Any]
    languages: dict[str, int]
    readme: str
    tree_paths: list[str]
    tree_truncated: bool
    descriptors: dict[str, str]
    good_first_issues: list[dict[str, Any]]
    help_wanted_issues: list[dict[str, Any]]


@dataclass
class StructureMetrics:
    total_files: int = 0
    total_dirs: int = 0
    top_level_dirs: list[str] = field(default_factory=list)
    extension_counts: dict[str, int] = field(default_factory=dict)
    has_tests: bool = False
    has_ci: bool = False
    has_docker: bool = False
    has_license: bool = False
    has_contributing: bool = False
    has_code_of_conduct: bool = False
    has_changelog: bool = False
    has_docs_dir: bool = False
    has_linter_config: bool = False
    has_type_config: bool = False
    has_gitignore: bool = False
    max_depth: int = 0


@dataclass
class Recommendation:
    title: str
    detail: str
    priority: str
    category: str


@dataclass
class Analysis:
    executive_summary: str
    tech_stack: list[str]
    strengths: list[str]
    architecture_patterns: list[str]
    code_organization: str
    recommendations: list[Recommendation]
    contribution_opportunities: list[str]


@dataclass
class Report:
    data: RepoData
    metrics: StructureMetrics
    health_score: int
    health_breakdown: dict[str, bool]
    analysis: Analysis
