import re

from analyzer.errors import InvalidRepositoryError
from analyzer.models import RepoRef

NAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
REPO_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
RESERVED_OWNERS = {
    "orgs", "users", "settings", "marketplace", "topics", "search", "explore",
    "features", "pricing", "about", "login", "join", "sponsors", "notifications",
}


def parse_repo_reference(value: str) -> RepoRef:
    text = (value or "").strip()
    if not text:
        raise InvalidRepositoryError("Enter a GitHub repository URL or owner/repo.")

    text = re.sub(r"^git@github\.com:", "https://github.com/", text, flags=re.IGNORECASE)
    text = re.sub(r"^(https?://)?(www\.)?github\.com/", "", text, flags=re.IGNORECASE)

    if re.match(r"^[a-z]+://", text, flags=re.IGNORECASE):
        raise InvalidRepositoryError("Only github.com repositories are supported.")

    text = text.split("?")[0].split("#")[0].strip("/")
    parts = [part for part in text.split("/") if part]
    if len(parts) < 2:
        raise InvalidRepositoryError(
            "Could not find an owner and repository name. Use the form owner/repo."
        )

    owner, name = parts[0], parts[1]
    if name.lower().endswith(".git"):
        name = name[:-4]

    if owner.lower() in RESERVED_OWNERS or not NAME_PATTERN.match(owner):
        raise InvalidRepositoryError(f"'{owner}' is not a valid GitHub owner name.")
    if not REPO_PATTERN.match(name) or name in {".", ".."}:
        raise InvalidRepositoryError(f"'{name}' is not a valid GitHub repository name.")
    return RepoRef(owner=owner, name=name)
