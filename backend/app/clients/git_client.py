"""
GitPython-based client for cloning and updating local repository copies.

Scope for Module 2 is intentionally limited to:
    - Cloning a repository into a target directory.
    - Fetching and pulling updates for an already-cloned repository.

No git history parsing, diffing, or metrics extraction happens here —
that is reserved for later modules (Module 4: Git History Analysis).
This client is deliberately independent of Module 1's `GitHubClient`;
it never calls the GitHub REST API and knows nothing about it.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from git import GitCommandError, InvalidGitRepositoryError, Repo

from app.core.exceptions import InvalidGitReferenceError, RepositoryCloneError

logger = logging.getLogger(__name__)


class GitRepositoryClient:
    """Thin wrapper around GitPython for clone/fetch/checkout/pull operations."""

    def clone(self, remote_url: str, destination: Path, branch: Optional[str] = None) -> Repo:
        """
        Clone a repository into `destination`.

        Args:
            remote_url: Clone URL, e.g. "https://github.com/owner/repo.git".
            destination: Local target directory. Must not already exist.
            branch: Optional branch to check out. Defaults to the remote's HEAD.

        Returns:
            The cloned `git.Repo` instance.

        Raises:
            RepositoryCloneError: On any git failure (network, auth, not found).
            InvalidGitReferenceError: If the requested branch does not exist.
        """
        logger.info(
            "Cloning %s into %s (branch=%s)", remote_url, destination, branch or "<default>"
        )
        try:
            clone_kwargs = {"branch": branch} if branch else {}
            return Repo.clone_from(remote_url, str(destination), **clone_kwargs)
        except GitCommandError as exc:
            self._raise_mapped_clone_error(exc, remote_url, branch)
            raise  # unreachable, satisfies type checkers

    def open_existing(self, path: Path) -> Repo:
        """
        Open an already-cloned local repository.

        Raises:
            RepositoryCloneError: If the directory is not a valid git repository.
        """
        try:
            return Repo(str(path))
        except InvalidGitRepositoryError as exc:
            raise RepositoryCloneError(
                f"Directory '{path}' exists but is not a valid git repository."
            ) from exc

    def fetch(self, repo: Repo) -> None:
        """Fetch all refs from the 'origin' remote."""
        try:
            repo.remotes.origin.fetch()
        except GitCommandError as exc:
            logger.error("Fetch failed for %s: %s", repo.working_dir, exc)
            raise RepositoryCloneError(f"Failed to fetch updates: {exc}") from exc

    def checkout(self, repo: Repo, branch: str) -> None:
        """
        Check out `branch`, creating a local tracking branch from
        `origin/<branch>` if it does not yet exist locally.

        Raises:
            InvalidGitReferenceError: If the branch does not exist on the remote.
        """
        try:
            if branch in [head.name for head in repo.heads]:
                repo.heads[branch].checkout()
                return

            remote_branch_names = [ref.name.split("/", 1)[-1] for ref in repo.remotes.origin.refs]
            if branch not in remote_branch_names:
                raise InvalidGitReferenceError(
                    f"Branch '{branch}' does not exist on the remote."
                )
            repo.git.checkout("-b", branch, f"origin/{branch}")
        except GitCommandError as exc:
            raise InvalidGitReferenceError(f"Unable to checkout branch '{branch}': {exc}") from exc

    def pull(self, repo: Repo, branch: str) -> None:
        """Pull the latest changes for `branch` from origin."""
        try:
            repo.remotes.origin.pull(branch)
        except GitCommandError as exc:
            logger.error("Pull failed for %s (branch=%s): %s", repo.working_dir, branch, exc)
            raise RepositoryCloneError(
                f"Failed to pull updates for branch '{branch}': {exc}"
            ) from exc

    @staticmethod
    def get_active_branch_name(repo: Repo) -> str:
        """Return the currently checked-out branch name."""
        try:
            return repo.active_branch.name
        except TypeError as exc:
            raise RepositoryCloneError(
                f"Repository at '{repo.working_dir}' is in a detached HEAD state."
            ) from exc

    @staticmethod
    def is_up_to_date(repo: Repo, branch: str) -> bool:
        """Return True if the local branch HEAD matches origin/branch HEAD."""
        local_commit = (
            repo.heads[branch].commit.hexsha if branch in [h.name for h in repo.heads] else None
        )
        if local_commit is None:
            return False
        try:
            remote_ref = next(
                ref for ref in repo.remotes.origin.refs if ref.name.split("/", 1)[-1] == branch
            )
        except StopIteration:
            return False
        return local_commit == remote_ref.commit.hexsha

    @staticmethod
    def get_last_commit_datetime(repo: Repo) -> datetime:
        """Return the commit timestamp of the current HEAD."""
        return repo.head.commit.committed_datetime

    def _raise_mapped_clone_error(
        self, exc: GitCommandError, remote_url: str, branch: Optional[str]
    ) -> None:
        """Translate a low-level GitCommandError into a typed app exception."""
        stderr = (exc.stderr or "").lower()

        branch_not_found_markers = (
            "not found",
            "reference is not a tree",
            "couldn't find remote ref",
            "remote branch",
        )
        if branch and any(marker in stderr for marker in branch_not_found_markers):
            raise InvalidGitReferenceError(
                f"Branch '{branch}' not found in repository '{remote_url}'."
            ) from exc

        if "repository not found" in stderr or "not found" in stderr:
            raise RepositoryCloneError(
                f"Repository '{remote_url}' was not found or is not accessible."
            ) from exc

        if "could not resolve host" in stderr or "unable to access" in stderr:
            raise RepositoryCloneError(
                f"Network error while cloning '{remote_url}'."
            ) from exc

        raise RepositoryCloneError(f"Failed to clone '{remote_url}': {exc}") from exc
