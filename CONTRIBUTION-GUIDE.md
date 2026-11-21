# Open-Source Contribution Guide

Part B of Task 3 needs a real issue or pull request on a real project. It has to come from your own account and reflect a problem you actually found, so it cannot be generated ahead of time. This guide shows a reliable way to do it within the 3 to 5 day window.

## 1. Choose a project

Pick an active Python, AI or developer-tooling project that you already use. Good signs:

- Commits within the last few weeks
- A `CONTRIBUTING.md` file
- Issues labelled `good first issue` or `documentation`
- Maintainers who reply to issues and pull requests

You can paste a candidate into the Task 3 analyzer and use its Contribute tab, which lists open beginner-friendly issues and a health checklist.

## 2. Find something genuine

The most defensible contributions come from using the project and noticing something real:

- Run the quick-start from the README on a clean environment. Any step that fails or is out of date is a documentation issue or fix.
- Read the docs for an unclear or incorrect statement, a broken link, or a missing example.
- Try an edge case and compare the behaviour with the documentation.
- Look at an existing `good first issue` that nobody has claimed, and comment before starting.

Avoid whitespace-only edits, punctuation tweaks and automated bulk changes. Maintainers reject them and the assessment says they count against you.

## 3. Check before you submit

- Search open and closed issues and pull requests for duplicates.
- Read `CONTRIBUTING.md` for commit message format, branch naming, tests and any contributor agreement.
- For anything beyond a small fix, open an issue first and wait for a maintainer to respond.

## 4. Submit

### If you open an issue

Include:

- A specific title
- Environment: operating system, Python version, package version
- Exact steps to reproduce, ideally a minimal snippet
- Expected result and actual result, with the full error text
- For feature proposals, the problem it solves and who benefits

### If you open a pull request

1. Fork the repository and create a branch with a descriptive name.
2. Make the smallest change that solves the problem.
3. Run the project's tests and linters.
4. Add or update tests and docs where relevant.
5. Reference the issue in the description, for example `Fixes #123`.
6. Explain what changed, why, and how you verified it.

## 5. Record it

Add the repository URL, the direct issue or PR link and a short summary into `SUBMISSION.md`. Keep the link public. Respond politely to maintainer feedback, because how you handle review is part of what is being assessed.
