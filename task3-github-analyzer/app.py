import os
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv

from analyzer import RepositoryAnalyzer
from analyzer.errors import AnalyzerError, AuthenticationError, RateLimitError
from analyzer.github_client import GitHubClient
from analyzer.llm import GroqAnalyzer
from analyzer.metrics import language_percentages

load_dotenv()

st.set_page_config(page_title="GitHub Repository AI Analyzer", page_icon="🔍", layout="wide")

PRIORITY_ICONS = {"high": "🔴", "medium": "🟠", "low": "🟢"}
EXAMPLES = ["pallets/flask", "tiangolo/fastapi", "psf/requests"]


def secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.getenv(name)


def format_reset(timestamp: int | None) -> str:
    if not timestamp:
        return ""
    moment = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return f" The limit resets at {moment:%H:%M} UTC."


def build_service(github_token: str | None) -> RepositoryAnalyzer:
    api_key = secret("GROQ_API_KEY")
    return RepositoryAnalyzer(GitHubClient(github_token), GroqAnalyzer(api_key=api_key))


def run_with_fallback(reference: str, token: str | None):
    try:
        return build_service(token).run(reference)
    except AuthenticationError:
        if not token:
            raise
        report = build_service(None).run(reference)
        st.warning("GitHub rejected the token, so this analysis ran without it and is limited to 60 requests per hour. Check the token in the sidebar or .env.")
        return report


def render_overview(report):
    meta = report.data.metadata
    st.subheader(report.data.ref.full_name)
    if meta.get("description"):
        st.write(meta["description"])
    if meta.get("topics"):
        st.write(" ".join(f"`{topic}`" for topic in meta["topics"]))

    columns = st.columns(5)
    columns[0].metric("Stars", f"{meta.get('stargazers_count', 0):,}")
    columns[1].metric("Forks", f"{meta.get('forks_count', 0):,}")
    columns[2].metric("Open issues", f"{meta.get('open_issues_count', 0):,}")
    columns[3].metric("License", (meta.get("license") or {}).get("spdx_id") or "None")
    columns[4].metric("Health score", f"{report.health_score}/100")

    st.link_button("Open on GitHub", meta.get("html_url", f"https://github.com/{report.data.ref.full_name}"))


def render_metrics(report):
    left, right = st.columns(2)
    with left:
        st.markdown("#### Languages (% of code)")
        percentages = language_percentages(report.data.languages)
        if percentages:
            st.bar_chart(percentages, horizontal=True)
        else:
            st.caption("No language data available.")
    with right:
        st.markdown("#### Repository health checklist")
        for label, passed in report.health_breakdown.items():
            st.write(f"{'✅' if passed else '❌'} {label}")

    st.markdown("#### Structure")
    metrics = report.metrics
    cols = st.columns(4)
    cols[0].metric("Files", f"{metrics.total_files:,}")
    cols[1].metric("Directories", f"{metrics.total_dirs:,}")
    cols[2].metric("Max depth", metrics.max_depth)
    cols[3].metric("Docker", "Yes" if metrics.has_docker else "No")
    if report.data.tree_truncated:
        st.caption("GitHub truncated the file listing for this very large repository, so counts are approximate.")
    if metrics.extension_counts:
        st.markdown("Most common file types")
        st.bar_chart(metrics.extension_counts)
    if metrics.top_level_dirs:
        st.markdown("Top-level directories: " + ", ".join(f"`{d}`" for d in metrics.top_level_dirs))


def render_analysis(report):
    analysis = report.analysis
    st.markdown("#### Executive summary")
    st.write(analysis.executive_summary)

    left, right = st.columns(2)
    with left:
        st.markdown("#### Tech stack")
        st.write(" ".join(f"`{item}`" for item in analysis.tech_stack) or "Not evident from the repository.")
        st.markdown("#### Strengths")
        for item in analysis.strengths:
            st.write(f"- {item}")
    with right:
        st.markdown("#### Architecture patterns")
        for item in analysis.architecture_patterns or ["No clear pattern evident."]:
            st.write(f"- {item}")
        st.markdown("#### Code organization")
        st.write(analysis.code_organization or "Not enough information.")

    st.markdown("#### Recommendations")
    for item in analysis.recommendations:
        with st.expander(f"{PRIORITY_ICONS[item.priority]} {item.title}  ·  {item.category}  ·  {item.priority} priority", expanded=item.priority == "high"):
            st.write(item.detail)


def render_contributions(report):
    st.markdown("#### Where a new contributor could help")
    for item in report.analysis.contribution_opportunities or ["No specific opportunities identified."]:
        st.write(f"- {item}")

    for title, issues in (("Open “good first issue” items", report.data.good_first_issues), ("Open “help wanted” items", report.data.help_wanted_issues)):
        st.markdown(f"#### {title}")
        if not issues:
            st.caption("None found.")
        for issue in issues:
            st.markdown(f"- [#{issue['number']} {issue['title']}]({issue['url']}) · {issue['comments']} comments")


def render_report(report):
    render_overview(report)
    tabs = st.tabs(["AI analysis", "Metrics", "Contribute"])
    with tabs[0]:
        render_analysis(report)
    with tabs[1]:
        render_metrics(report)
    with tabs[2]:
        render_contributions(report)


def main():
    st.title("🔍 GitHub Repository AI Analyzer")
    st.caption("Paste a public repository to get metrics, an AI-written technical review and contribution ideas.")

    with st.sidebar:
        st.header("Settings")
        override = st.text_input(
            "Override GitHub token (optional)",
            type="password",
            value="",
            autocomplete="new-password",
            help="Leave empty to use GITHUB_TOKEN from .env or secrets. Raises the GitHub API limit from 60 to 5,000 requests per hour.",
        )
        env_token = secret("GITHUB_TOKEN")
        token = override.strip() or (env_token or "").strip()
        if override.strip():
            st.caption("Using the token typed above.")
        elif token:
            st.caption("Using GITHUB_TOKEN from the environment.")
        else:
            st.caption("No token set. Limited to 60 GitHub requests per hour.")
        st.header("Examples")
        for example in EXAMPLES:
            if st.button(example, use_container_width=True):
                st.session_state.repo_input = example

    if "repo_input" not in st.session_state:
        st.session_state.repo_input = ""

    with st.form("analyze"):
        reference = st.text_input("Repository", key="repo_input", placeholder="https://github.com/owner/repo or owner/repo")
        submitted = st.form_submit_button("Analyze", type="primary")

    if submitted:
        try:
            with st.spinner("Fetching repository data and generating analysis..."):
                st.session_state.report = run_with_fallback(reference, token.strip() or None)
        except RateLimitError as exc:
            st.session_state.pop("report", None)
            st.warning(f"{exc}{format_reset(exc.reset_at)}")
        except AnalyzerError as exc:
            st.session_state.pop("report", None)
            st.error(str(exc))
        except Exception:
            st.session_state.pop("report", None)
            st.error("Something unexpected went wrong. Please try again.")

    report = st.session_state.get("report")
    if report:
        render_report(report)


main()
