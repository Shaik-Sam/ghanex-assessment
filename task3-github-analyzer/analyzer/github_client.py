import base64
import binascii
from typing import Any

import requests

from analyzer.errors import (
    AuthenticationError,
    EmptyRepositoryError,
    GitHubAPIError,
    RateLimitError,
    RepositoryNotFoundError,
)
from analyzer.models import RepoData, RepoRef

API_ROOT = "https://api.github.com"

DESCRIPTOR_FILES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
)

MAX_DESCRIPTOR_CHARS = 3000
MAX_README_CHARS = 20000


class GitHubClient:
    def __init__(self, token: str | None = None, timeout: float = 15.0, session: requests.Session | None = None):
        self.timeout = timeout
        self.authenticated = bool(token)
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ghanex-assessment-repo-analyzer",
            }
        )
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _get(self, path: str, params: dict[str, Any] | None = None, allow_404: bool = False) -> Any:
        url = path if path.startswith("http") else f"{API_ROOT}{path}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.Timeout as exc:
            raise GitHubAPIError("GitHub did not respond in time. Try again shortly.") from exc
        except requests.ConnectionError as exc:
            raise GitHubAPIError("Could not connect to GitHub. Check your internet connection.") from exc
        except requests.RequestException as exc:
            raise GitHubAPIError(f"Request to GitHub failed: {exc}") from exc

        if response.status_code == 404:
            if allow_404:
                return None
            raise RepositoryNotFoundError(
                "Repository not found. It may not exist, or it may be private."
            )
        if self._is_rate_limited(response):
            reset = response.headers.get("X-RateLimit-Reset")
            hint = "" if self.authenticated else " Adding a GitHub token raises the limit to 5,000 requests per hour."
            raise RateLimitError(
                "GitHub API rate limit reached." + hint,
                reset_at=int(reset) if reset and reset.isdigit() else None,
            )
        if response.status_code == 401:
            raise AuthenticationError("The GitHub token was rejected. Check that it is valid and not expired.")
        if response.status_code == 403:
            raise GitHubAPIError("Access to this repository is forbidden. It may be private or restricted.")
        if response.status_code == 409:
            if allow_404:
                return None
            raise EmptyRepositoryError("This repository is empty.")
        if response.status_code >= 400:
            raise GitHubAPIError(f"GitHub returned HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise GitHubAPIError("GitHub returned an unreadable response.") from exc

    @staticmethod
    def _is_rate_limited(response: Any) -> bool:
        if response.status_code == 429:
            return True
        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining == "0":
                return True
            try:
                message = (response.json() or {}).get("message", "")
            except ValueError:
                message = ""
            return "rate limit" in message.lower()
        return False

    @staticmethod
    def _decode(payload: dict[str, Any] | None) -> str:
        if not payload or payload.get("encoding") != "base64":
            return ""
        try:
            return base64.b64decode(payload.get("content", "")).decode("utf-8", errors="replace")
        except (binascii.Error, ValueError):
            return ""

    def get_metadata(self, ref: RepoRef) -> dict[str, Any]:
        return self._get(f"/repos/{ref.owner}/{ref.name}")

    def get_languages(self, ref: RepoRef) -> dict[str, int]:
        return self._get(f"/repos/{ref.owner}/{ref.name}/languages", allow_404=True) or {}

    def get_readme(self, ref: RepoRef) -> str:
        text = self._decode(self._get(f"/repos/{ref.owner}/{ref.name}/readme", allow_404=True))
        return text[:MAX_README_CHARS]

    def get_tree(self, ref: RepoRef, branch: str) -> tuple[list[str], bool]:
        payload = self._get(
            f"/repos/{ref.owner}/{ref.name}/git/trees/{branch}", {"recursive": "1"}, allow_404=True
        )
        if not payload:
            return [], False
        paths = [item["path"] for item in payload.get("tree", []) if item.get("type") in ("blob", "tree")]
        return paths, bool(payload.get("truncated"))

    def get_file(self, ref: RepoRef, path: str) -> str:
        payload = self._get(f"/repos/{ref.owner}/{ref.name}/contents/{path}", allow_404=True)
        if isinstance(payload, list):
            return ""
        return self._decode(payload)[:MAX_DESCRIPTOR_CHARS]

    def get_issues(self, ref: RepoRef, label: str, limit: int = 5) -> list[dict[str, Any]]:
        payload = self._get(
            f"/repos/{ref.owner}/{ref.name}/issues",
            {"labels": label, "state": "open", "per_page": 15, "sort": "updated"},
            allow_404=True,
        )
        issues = [item for item in (payload or []) if "pull_request" not in item]
        return [
            {
                "number": item["number"],
                "title": item["title"],
                "url": item["html_url"],
                "comments": item.get("comments", 0),
            }
            for item in issues[:limit]
        ]

    def fetch(self, ref: RepoRef) -> RepoData:
        metadata = self.get_metadata(ref)
        full_ref = RepoRef(owner=metadata["owner"]["login"], name=metadata["name"])
        branch = metadata.get("default_branch") or "main"
        tree_paths, truncated = self.get_tree(full_ref, branch)
        if metadata.get("size", 1) == 0 and not tree_paths:
            raise EmptyRepositoryError("This repository is empty.")

        top_level_files = {path for path in tree_paths if "/" not in path}
        descriptors: dict[str, str] = {}
        for name in DESCRIPTOR_FILES:
            if name in top_level_files:
                content = self.get_file(full_ref, name)
                if content:
                    descriptors[name] = content

        return RepoData(
            ref=full_ref,
            metadata=metadata,
            languages=self.get_languages(full_ref),
            readme=self.get_readme(full_ref),
            tree_paths=tree_paths,
            tree_truncated=truncated,
            descriptors=descriptors,
            good_first_issues=self.get_issues(full_ref, "good first issue"),
            help_wanted_issues=self.get_issues(full_ref, "help wanted"),
        )
