"""
Service layer for Module 2 — Repository Cloner.

Orchestrates:
    1. Parsing the repository URL into (owner, repo) — reusing the exact
       same `parse_owner_repo` utility Module 1 uses, so URL validation
       rules stay identical across modules.
    2. Deciding whether to clone fresh, update an existing copy, or
       report it as already up to date.
    3. Delegating all actual git operations to `GitRepositoryClient`.
    4. Assembling the `RepositoryCloneResult`.

This service does not talk to the GitHub REST API — Module 1 already
validated the repository's existence at the metadata stage. Module 2 is
concerned only with getting a working local copy onto disk.
"""

import logging
from pathlib import Path
from typing import Optional

from app.clients.git_client import GitRepositoryClient
from app.core.config import Settings, get_settings
from app.schemas.clone_result import CloneStatus, RepositoryCloneResult
from app.utils.github_url_parser import parse_owner_repo

logger = logging.getLogger(__name__)


class RepositoryClonerService:
    """Clones or updates a local working copy of a public GitHub repository."""

    def __init__(self, git_client: GitRepositoryClient, settings: Optional[Settings] = None) -> None:
        self._git_client = git_client
        self._settings = settings or get_settings()

    def clone_or_update_repository(
        self, repository_url: str, branch: Optional[str] = None
    ) -> RepositoryCloneResult:
        """
        Clone the repository if no local copy exists, or update it in place.

        Args:
            repository_url: Public GitHub repository URL.
            branch: Optional branch to check out. Defaults to the
                repository's default branch (fresh clone) or the branch
                already checked out locally (existing copy).

        Returns:
            A populated `RepositoryCloneResult`.

        Raises:
            InvalidRepositoryURLError: If the URL cannot be parsed.
            InvalidGitReferenceError: If the requested branch does not exist.
            RepositoryCloneError: For any other git failure.
        """
        owner, repo = parse_owner_repo(repository_url)
        local_path = self._resolve_local_path(owner, repo)

        if not local_path.exists():
            return self._clone_fresh(repository_url, local_path, owner, repo, branch)

        return self._update_existing(local_path, owner, repo, branch)

    def _resolve_local_path(self, owner: str, repo: str) -> Path:
        """Build the managed workspace path: workspace_directory/{owner}_{repo}."""
        workspace_dir = Path(self._settings.workspace_directory)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        return workspace_dir / f"{owner}_{repo}"

    @staticmethod
    def _normalize_clone_url(repository_url: str) -> str:
        """Ensure the clone URL is in a form git can use directly (ends in .git)."""
        url = repository_url.strip().rstrip("/")
        if url.startswith(("http://", "https://")) and not url.endswith(".git"):
            url = f"{url}.git"
        return url

    def _clone_fresh(
        self,
        repository_url: str,
        local_path: Path,
        owner: str,
        repo: str,
        branch: Optional[str],
    ) -> RepositoryCloneResult:
        """
        Perform a fresh clone into `local_path`.

        Uses `clone_with_recovery` rather than a single plain `clone` call:
        transient transport failures (connection resets, stalls - see
        `app.clients.git_client` for the full marker list) are retried
        automatically with tuned git transport settings, and as a final
        history-preserving fallback, one `--filter=blob:none` partial clone
        is attempted if full clones keep failing transiently. Permanent
        failures (repository not found, private, bad branch) are never
        retried and surface exactly as before.
        """
        clone_url = self._normalize_clone_url(repository_url)
        git_repo = self._git_client.clone_with_recovery(
            clone_url,
            local_path,
            branch,
            max_attempts=self._settings.clone_max_attempts,
            backoff_seconds=self._settings.clone_retry_backoff_seconds,
            post_buffer_bytes=self._settings.clone_http_post_buffer_bytes,
            low_speed_limit_bytes=self._settings.clone_http_low_speed_limit_bytes,
            low_speed_time_seconds=self._settings.clone_http_low_speed_time_seconds,
            partial_clone_fallback_enabled=self._settings.clone_partial_clone_fallback_enabled,
        )
        resolved_branch = branch or self._git_client.get_active_branch_name(git_repo)

        logger.info("Cloned %s/%s into %s (branch=%s)", owner, repo, local_path, resolved_branch)

        return RepositoryCloneResult(
            owner=owner,
            repository=repo,
            branch=resolved_branch,
            local_path=str(local_path),
            status=CloneStatus.CLONED,
            last_updated=self._git_client.get_last_commit_datetime(git_repo),
        )

    def _update_existing(
        self, local_path: Path, owner: str, repo: str, branch: Optional[str]
    ) -> RepositoryCloneResult:
        """Fetch/pull an already-cloned repository instead of re-cloning it."""
        git_repo = self._git_client.open_existing(local_path)
        self._git_client.fetch(git_repo)

        target_branch = branch or self._git_client.get_active_branch_name(git_repo)

        if self._git_client.get_active_branch_name(git_repo) != target_branch:
            self._git_client.checkout(git_repo, target_branch)

        if self._git_client.is_up_to_date(git_repo, target_branch):
            logger.info("%s/%s already up to date at %s", owner, repo, local_path)
            status = CloneStatus.ALREADY_EXISTS
        else:
            self._git_client.pull(git_repo, target_branch)
            logger.info("Updated %s/%s at %s (branch=%s)", owner, repo, local_path, target_branch)
            status = CloneStatus.UPDATED

        return RepositoryCloneResult(
            owner=owner,
            repository=repo,
            branch=target_branch,
            local_path=str(local_path),
            status=status,
            last_updated=self._git_client.get_last_commit_datetime(git_repo),
        )
