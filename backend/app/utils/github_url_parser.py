"""
Utility for extracting `(owner, repo)` from a GitHub repository URL.

Supported formats:
    https://github.com/owner/repo
    https://github.com/owner/repo/
    https://github.com/owner/repo.git
    http://github.com/owner/repo
    github.com/owner/repo
"""

import re
from typing import Tuple

from app.core.exceptions import InvalidRepositoryURLError

# Matches: (optional scheme)(optional www.)github.com/<owner>/<repo>(optional .git)(optional trailing /)
_GITHUB_URL_PATTERN = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/"
    r"(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+?)"
    r"(?:\.git)?/?$"
)


def parse_owner_repo(repository_url: str) -> Tuple[str, str]:
    """
    Extract the `(owner, repo)` pair from a GitHub repository URL.

    Args:
        repository_url: A GitHub repository URL, e.g.
            "https://github.com/fastapi/fastapi".

    Returns:
        A tuple of (owner, repo).

    Raises:
        InvalidRepositoryURLError: If the URL does not match a valid
            GitHub repository URL format.
    """
    if not repository_url or not repository_url.strip():
        raise InvalidRepositoryURLError("Repository URL must not be empty.")

    match = _GITHUB_URL_PATTERN.match(repository_url.strip())
    if not match:
        raise InvalidRepositoryURLError(
            f"'{repository_url}' is not a valid GitHub repository URL. "
            "Expected format: https://github.com/<owner>/<repo>"
        )

    owner = match.group("owner")
    repo = match.group("repo")
    return owner, repo
