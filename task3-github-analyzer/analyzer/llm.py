import json
import os
import re
from typing import Any

from analyzer.errors import LLMError
from analyzer.models import Analysis, Recommendation, RepoData, StructureMetrics
from analyzer.metrics import language_percentages

SYSTEM_PROMPT = (
    "You are a senior software engineer reviewing an open-source repository for a prospective contributor. "
    "Use only the facts provided. If something is not evident from the data, say so instead of guessing. "
    "Respond with a single JSON object and nothing else, using exactly these keys: "
    "executive_summary (string, 3 to 5 sentences covering purpose and tech stack), "
    "tech_stack (array of short strings), "
    "strengths (array of 3 to 6 strings), "
    "architecture_patterns (array of strings describing patterns evident from the structure), "
    "code_organization (string, 2 to 4 sentences), "
    "recommendations (array of at least 3 objects, each with title, detail, priority and category; "
    "priority is one of high, medium, low; category is one of testing, documentation, ci_cd, architecture, security, tooling, community), "
    "contribution_opportunities (array of 3 to 6 strings naming concrete places a new contributor could help). "
    "Recommendations must be specific to this repository and actionable, not generic advice."
)

PRIORITIES = ("high", "medium", "low")
CATEGORIES = ("testing", "documentation", "ci_cd", "architecture", "security", "tooling", "community")
MAX_TREE_PATHS = 250
MAX_README_IN_PROMPT = 6000


def build_prompt(data: RepoData, metrics: StructureMetrics) -> str:
    meta = data.metadata
    license_info = (meta.get("license") or {}).get("spdx_id") or "none detected"
    facts = {
        "name": data.ref.full_name,
        "description": meta.get("description"),
        "primary_language": meta.get("language"),
        "languages_percent": language_percentages(data.languages),
        "stars": meta.get("stargazers_count"),
        "forks": meta.get("forks_count"),
        "open_issues": meta.get("open_issues_count"),
        "license": license_info,
        "topics": meta.get("topics", []),
        "created_at": meta.get("created_at"),
        "last_push": meta.get("pushed_at"),
        "archived": meta.get("archived"),
    }
    structure = {
        "total_files": metrics.total_files,
        "top_level_directories": metrics.top_level_dirs,
        "top_file_extensions": metrics.extension_counts,
        "has_tests": metrics.has_tests,
        "has_ci": metrics.has_ci,
        "has_docker": metrics.has_docker,
        "has_contributing_guide": metrics.has_contributing,
        "has_docs_directory": metrics.has_docs_dir,
        "has_linter_config": metrics.has_linter_config,
        "has_changelog": metrics.has_changelog,
    }
    tree_sample = sorted(data.tree_paths, key=lambda p: (p.count("/"), p))[:MAX_TREE_PATHS]
    descriptors = "\n\n".join(f"--- {name} ---\n{content}" for name, content in data.descriptors.items()) or "none found"
    issues = [f"#{i['number']} {i['title']}" for i in data.good_first_issues + data.help_wanted_issues]

    return (
        f"REPOSITORY FACTS\n{json.dumps(facts, indent=2, default=str)}\n\n"
        f"STRUCTURE METRICS\n{json.dumps(structure, indent=2)}\n\n"
        f"FILE TREE (shallowest first, {len(tree_sample)} of {len(data.tree_paths)} paths"
        f"{', GitHub truncated the full listing' if data.tree_truncated else ''})\n" + "\n".join(tree_sample) + "\n\n"
        f"PACKAGE DESCRIPTORS\n{descriptors}\n\n"
        f"OPEN BEGINNER-FRIENDLY ISSUES\n{chr(10).join(issues) or 'none labelled'}\n\n"
        f"README (truncated)\n{data.readme[:MAX_README_IN_PROMPT] or 'no README found'}"
    )


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise LLMError("The model did not return structured JSON.")
        try:
            value = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError("The model returned malformed JSON.") from exc
    if not isinstance(value, dict):
        raise LLMError("The model returned an unexpected structure.")
    return value


def _strings(value: Any, limit: int = 8) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:limit]


def parse_analysis(payload: dict[str, Any]) -> Analysis:
    summary = str(payload.get("executive_summary", "")).strip()
    if not summary:
        raise LLMError("The model response is missing an executive summary.")

    recommendations = []
    for item in payload.get("recommendations") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        detail = str(item.get("detail", "")).strip()
        if not title or not detail:
            continue
        priority = str(item.get("priority", "medium")).lower().strip()
        category = str(item.get("category", "tooling")).lower().strip().replace("-", "_").replace("/", "_")
        recommendations.append(
            Recommendation(
                title=title,
                detail=detail,
                priority=priority if priority in PRIORITIES else "medium",
                category=category if category in CATEGORIES else "tooling",
            )
        )
    if len(recommendations) < 3:
        raise LLMError("The model returned fewer than three usable recommendations.")

    return Analysis(
        executive_summary=summary,
        tech_stack=_strings(payload.get("tech_stack"), 12),
        strengths=_strings(payload.get("strengths")),
        architecture_patterns=_strings(payload.get("architecture_patterns")),
        code_organization=str(payload.get("code_organization", "")).strip(),
        recommendations=recommendations,
        contribution_opportunities=_strings(payload.get("contribution_opportunities")),
    )


class GroqAnalyzer:
    def __init__(self, model: str | None = None, api_key: str | None = None, client: Any = None, retries: int = 1):
        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.retries = retries
        if client is not None:
            self._client = client
            return
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise LLMError("GROQ_API_KEY is not set. Add it to your environment or Streamlit secrets.")
        from groq import Groq

        self._client = Groq(api_key=key)

    def _request(self, prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            names = {cls.__name__ for cls in type(exc).__mro__}
            if "RateLimitError" in names:
                raise LLMError("The language model rate limit was reached. Wait a moment and try again.") from exc
            if "APIConnectionError" in names:
                raise LLMError("Could not reach the language model service.") from exc
            if "NotFoundError" in names:
                raise LLMError(f"The model '{self.model}' is not available on your Groq account. Set GROQ_MODEL to a supported model such as openai/gpt-oss-120b.") from exc
            if "AuthenticationError" in names:
                raise LLMError("The language model API key was rejected.") from exc
            raise LLMError(f"The language model request failed: {exc}") from exc
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMError("The language model returned an empty response.")
        return content

    def analyze(self, data: RepoData, metrics: StructureMetrics) -> Analysis:
        prompt = build_prompt(data, metrics)
        last_error: LLMError | None = None
        for _ in range(self.retries + 1):
            try:
                return parse_analysis(extract_json(self._request(prompt)))
            except LLMError as exc:
                last_error = exc
                if "rate limit" in str(exc) or "API key" in str(exc):
                    raise
        raise last_error or LLMError("Analysis failed.")
