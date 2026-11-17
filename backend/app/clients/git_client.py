"""
GitPython-based client for cloning and updating local repository copies.

Scope for Module 2 is intentionally limited to:
    - Cloning a repository into a target directory.
    - Fetching and pulling updates for an already-cloned repository.

No git history parsing, diffing, or metrics extraction happens here —
that is reserved for later modules (Module 4: Git History Analysis).
This client is deliberately independent of Module 1's `GitHubClient`;
it never calls the GitHub REST API and knows nothing about it.

`clone()` performs a single plain clone attempt, unchanged from before.
`clone_with_recovery()` is a new, additive entry point that wraps it with
transport tuning, automatic retry for transient transfer failures, and a
blobless partial-clone fallback - all to handle the class of "RPC failed",
"early EOF", "invalid index-pack output" errors GitHub's Smart HTTP
transport can produce for larger repositories, without ever shallow-
cloning (which would destroy the history Module 4 depends on).
"""

import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from git import GitCommandError, InvalidGitRepositoryError, Repo

from app.core.exceptions import InvalidGitReferenceError, RepositoryCloneError

logger = logging.getLogger(__name__)

# stderr substrings that indicate a transient transport/network failure worth
# retrying - connection resets, stalls, and timeouts during the fetch-pack /
# index-pack phase. Deliberately distinct from permanent-failure markers
# (not found, auth, access rights) in `_raise_mapped_clone_error`, which are
# never retried.
_TRANSIENT_ERROR_MARKERS = (
    "rpc failed",
    "early eof",
    "unexpected disconnect",
    "the remote end hung up unexpectedly",
    "recv failure",
    "connection was reset",
    "connection reset",
    "connection timed out",
    "operation timed out",
    "could not resolve host",
    "temporary failure in name resolution",
    "transfer closed with outstanding read data remaining",
    "invalid index-pack output",
    "fetch-pack: invalid index-pack output",
    "index-pack failed",
    "unable to access",
    "ssl_read",
    "gnutls_handshake",
    "connection reset by peer",
)


def is_transient_clone_error(exc: GitCommandError) -> bool:
    """True if `exc` looks like a transient network/transport failure worth retrying."""
    stderr = (exc.stderr or "").lower()
    return any(marker in stderr for marker in _TRANSIENT_ERROR_MARKERS)


class GitRepositoryClient:
    """Thin wrapper around GitPython for clone/fetch/checkout/pull operations."""

    def clone(self, remote_url: str, destination: Path, branch: Optional[str] = None) -> Repo:
        """
        Clone a repository into `destination`. A single plain attempt, with
        no retry or transport tuning - unchanged from before.

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

    def clone_with_recovery(
        self,
        remote_url: str,
        destination: Path,
        branch: Optional[str],
        max_attempts: int,
        backoff_seconds: float,
        post_buffer_bytes: int,
        low_speed_limit_bytes: int,
        low_speed_time_seconds: int,
        partial_clone_fallback_enabled: bool,
    ) -> Repo:
        """
        Clone `destination`, automatically retrying transient transport
        failures with git transport tuning, and falling back to one
        `--filter=blob:none` partial clone (full history, deferred file
        content) if full-clone retries are exhausted on a still-transient
        failure.

        `destination` must not exist on entry; a partial directory from a
        previous failed attempt is removed before each retry so it can
        never be mistaken for a valid workspace.

        Raises:
            RepositoryCloneError: Permanent failure, or transient failure
                that persisted through every attempt and the fallback.
            InvalidGitReferenceError: If the requested branch does not exist.
        """
        transport_config = self._transport_config(post_buffer_bytes, low_speed_limit_bytes, low_speed_time_seconds)
        last_exc: Optional[GitCommandError] = None

        for attempt in range(1, max_attempts + 1):
            self._clean_destination(destination)
            try:
                clone_kwargs = {"branch": branch} if branch else {}
                logger.info(
                    "Cloning %s into %s (attempt %d/%d, branch=%s)",
                    remote_url, destination, attempt, max_attempts, branch or "<default>",
                )
                return Repo.clone_from(
                    remote_url, str(destination), multi_options=transport_config,
                    allow_unsafe_options=True, **clone_kwargs
                )
            except GitCommandError as exc:
                last_exc = exc
                if not is_transient_clone_error(exc):
                    # Permanent failure (not found, auth, bad branch, ...): no point retrying.
                    self._clean_destination(destination)
                    self._raise_mapped_clone_error(exc, remote_url, branch)
                logger.warning(
                    "Transient clone failure for %s on attempt %d/%d: %s",
                    remote_url, attempt, max_attempts, (exc.stderr or str(exc)).strip().splitlines()[-1:],
                )
                if attempt < max_attempts:
                    time.sleep(backoff_seconds * attempt)

        # Every full-clone attempt failed transiently. Try one blobless
        # partial clone: it still fetches the complete commit graph (all
        # commits, authors, dates, branches - everything Module 4 needs,
        # since it only ever calls `iter_commits`) but defers individual
        # file content, avoiding the large single-shot transfer that was
        # most likely the actual cause of the resets above.
        if partial_clone_fallback_enabled:
            self._clean_destination(destination)
            try:
                logger.info(
                    "Full clone of %s failed after %d attempts; trying a partial "
                    "clone (--filter=blob:none) as a history-preserving fallback",
                    remote_url, max_attempts,
                )
                clone_kwargs = {"branch": branch} if branch else {}
                return Repo.clone_from(
                    remote_url, str(destination),
                    multi_options=transport_config,
                    filter="blob:none",
                    allow_unsafe_options=True,
                    **clone_kwargs,
                )
            except GitCommandError as fallback_exc:
                last_exc = fallback_exc
                logger.error("Partial-clone fallback for %s also failed: %s", remote_url, fallback_exc.stderr or fallback_exc)

        self._clean_destination(destination)
        self._raise_mapped_clone_error(last_exc, remote_url, branch)
        raise  # unreachable, satisfies type checkers

    @staticmethod
    def _transport_config(post_buffer_bytes: int, low_speed_limit_bytes: int, low_speed_time_seconds: int) -> List[str]:
        # GitPython blocks `-c` by default (it can otherwise be used to run
        # arbitrary commands via crafted config values) and requires
        # `allow_unsafe_options=True` to pass it. That's safe here: every
        # value below comes from our own Settings (ultimately int/float
        # config, never user input - the repository URL is a separate,
        # unrelated argument to `clone_from`), not from the requested
        # repository URL or anything else user-controlled.
        return [
            f"-c http.postBuffer={post_buffer_bytes}",
            f"-c http.lowSpeedLimit={low_speed_limit_bytes}",
            f"-c http.lowSpeedTime={low_speed_time_seconds}",
        ]

    @staticmethod
    def _clean_destination(destination: Path) -> None:
        """Remove any partial/failed clone directory so it is never mistaken for a valid workspace."""
        if destination.exists():
            logger.info("Removing incomplete workspace at %s before (re)cloning", destination)
            shutil.rmtree(destination, ignore_errors=True)

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
