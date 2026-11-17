"""
Service layer for Module 1 — GitHub Repository Metadata Collector.

Orchestrates:
    1. Parsing the incoming repository URL into (owner, repo).
    2. Calling GitHubClient for repository details + languages.
    3. Mapping the raw GitHub JSON payloads into `RepositoryMetadata`.

This is the only layer that knows how to translate GitHub's raw response
shape into the platform's schema. The API layer and client layer stay
decoupled from that mapping logic.
"""

import logging
from typing import Any, Dict

from app.clients.github_client import GitHubClient
from app.schemas.repository import RepositoryMetadata, RepositoryOwner
from app.utils.github_url_parser import parse_owner_repo

logger = logging.getLogger(__name__)


class RepositoryService:
    """Collects and assembles repository metadata for a given GitHub URL."""

    def __init__(self, github_client: GitHubClient) -> None:
        self._github_client = github_client

    async def analyze_repository(self, repository_url: str) -> RepositoryMetadata:
        """
        Collect repository metadata + language breakdown for a GitHub URL.

        Args:
            repository_url: Public GitHub repository URL.

        Returns:
            A populated `RepositoryMetadata` object.

        Raises:
            InvalidRepositoryURLError: If the URL cannot be parsed.
            RepositoryNotFoundError: If GitHub returns 404.
            GitHubAuthenticationError: If the GitHub token is invalid.
            GitHubRateLimitExceededError: If GitHub rate limits are hit.
            GitHubAPIError: For any other GitHub API failure.
        """
        owner, repo = parse_owner_repo(repository_url)
        logger.info("Analyzing repository metadata for %s/%s", owner, repo)

        repo_data = await self._github_client.get_repository(owner, repo)
        languages = await self._github_client.get_repository_languages(owner, repo)

        metadata = self._map_to_schema(repo_data, languages)
        logger.info("Successfully collected metadata for %s/%s", owner, repo)
        return metadata

    @staticmethod
    def _map_to_schema(
        repo_data: Dict[str, Any], languages: Dict[str, int]
    ) -> RepositoryMetadata:
        """Map raw GitHub JSON payloads into a `RepositoryMetadata` instance."""
        owner_data = repo_data.get("owner") or {}
        license_data = repo_data.get("license")

        # Primary language: highest byte count in the languages breakdown.
        primary_language = max(languages, key=languages.get) if languages else repo_data.get("language")

        return RepositoryMetadata(
            full_name=repo_data["full_name"],
            owner=RepositoryOwner(
                login=owner_data.get("login", "unknown"),
                type=owner_data.get("type", "unknown"),
                avatar_url=owner_data.get("avatar_url"),
            ),
            description=repo_data.get("description"),
            html_url=repo_data["html_url"],
            default_branch=repo_data.get("default_branch", "main"),
            visibility=repo_data.get("visibility", "public"),
            is_archived=repo_data.get("archived", False),
            is_fork=repo_data.get("fork", False),
            stargazers_count=repo_data.get("stargazers_count", 0),
            forks_count=repo_data.get("forks_count", 0),
            watchers_count=repo_data.get("watchers_count", 0),
            open_issues_count=repo_data.get("open_issues_count", 0),
            size_kb=repo_data.get("size", 0),
            license_name=license_data.get("name") if license_data else None,
            topics=repo_data.get("topics", []),
            primary_language=primary_language,
            languages=languages,
            created_at=repo_data["created_at"],
            updated_at=repo_data["updated_at"],
            pushed_at=repo_data.get("pushed_at"),
        )
