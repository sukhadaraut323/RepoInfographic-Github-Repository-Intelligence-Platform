"""
GitHistoryAnalyzer — Module 4 component.

Reads commit and branch metadata directly from a local `.git` directory
using GitPython. This component never executes repository code and never
calls the GitHub REST API — it only reads git object metadata already
present on disk (as cloned by Module 2).

It is intentionally independent of Module 2's `GitRepositoryClient`:
Module 4 must be able to analyze any local git repository on its own,
without depending on how it got there.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from git import GitCommandError, InvalidGitRepositoryError, NoSuchPathError, Repo
from git.exc import GitError

from app.core.exceptions import (
    GitHistoryAnalysisError,
    NotAGitRepositoryError,
    RepositoryPathNotFoundError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommitInfo:
    """Lightweight, GitPython-independent representation of a single commit."""

    sha: str
    author_name: str
    author_email: str
    committed_datetime: datetime


class GitHistoryAnalyzer:
    """Extracts raw commit and branch metadata from a local git repository."""

    def open_repository(self, path: Path) -> Repo:
        """
        Open the git repository at `path`.

        Raises:
            RepositoryPathNotFoundError: If `path` does not exist or is not a directory.
            NotAGitRepositoryError: If `path` is not a valid git repository.
        """
        if not path.exists() or not path.is_dir():
            raise RepositoryPathNotFoundError(
                f"Local repository path '{path}' does not exist or is not a directory. "
                "Ensure the repository has been cloned via Module 2 first."
            )
        try:
            return Repo(str(path))
        except InvalidGitRepositoryError as exc:
            raise NotAGitRepositoryError(
                f"'{path}' exists but is not a valid git repository (no '.git' metadata found)."
            ) from exc
        except NoSuchPathError as exc:
            raise RepositoryPathNotFoundError(f"Local repository path '{path}' does not exist.") from exc

    def get_commits(self, repo: Repo) -> List[CommitInfo]:
        """
        Return every commit reachable from any ref (i.e. `git log --all`).

        An empty repository (no commits yet) yields an empty list rather
        than raising — this is normal GitPython behavior and is treated
        as a graceful, valid state, not an error.

        Raises:
            GitHistoryAnalysisError: If commit history cannot be read due
                to corrupted or unreadable git metadata.
        """
        try:
            commits = list(repo.iter_commits("--all"))
            return [
                CommitInfo(
                    sha=commit.hexsha,
                    author_name=commit.author.name or "unknown",
                    author_email=(commit.author.email or "unknown").lower(),
                    committed_datetime=commit.committed_datetime,
                )
                for commit in commits
            ]
        except (GitCommandError, ValueError, GitError) as exc:
            raise GitHistoryAnalysisError(
                f"Failed to read commit history for '{repo.working_dir}': {exc}"
            ) from exc

    def get_branch_names(self, repo: Repo) -> List[str]:
        """
        Return the repository's branch names.

        Prefers remote-tracking branches (`origin/*`, excluding the
        symbolic `HEAD` ref) since a fresh clone typically checks out
        only one local branch, while the remote reflects the repository's
        full branch set. Falls back to local branches if no remote exists.

        Raises:
            GitHistoryAnalysisError: If branch metadata cannot be read.
        """
        try:
            if repo.remotes:
                origin = repo.remotes.origin
                names = sorted(
                    {
                        ref.name.split("/", 1)[-1]
                        for ref in origin.refs
                        if ref.name.split("/", 1)[-1] != "HEAD"
                    }
                )
                if names:
                    return names
            return sorted(head.name for head in repo.heads)
        except (GitCommandError, AttributeError, GitError) as exc:
            raise GitHistoryAnalysisError(
                f"Failed to read branch information for '{repo.working_dir}': {exc}"
            ) from exc

    def get_default_branch(self, repo: Repo, branch_names: List[str]) -> Optional[str]:
        """
        Best-effort determination of the repository's default branch.

        Resolution order:
            1. The currently checked-out branch (`repo.active_branch`).
            2. The remote's symbolic HEAD (`origin/HEAD` -> e.g. "main").
            3. The first known branch name, alphabetically.
            4. None, if the repository has no branches (e.g. it is empty).
        """
        try:
            return repo.active_branch.name
        except (TypeError, ValueError):
            pass  # detached HEAD or unborn branch reference — fall through

        try:
            if repo.remotes:
                head_ref = repo.remotes.origin.refs.HEAD
                return head_ref.reference.name.split("/", 1)[-1]
        except (AttributeError, GitCommandError, IndexError, GitError):
            pass

        return branch_names[0] if branch_names else None
