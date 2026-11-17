"""
Thin async client around the GitHub REST API.

Scope for Module 1 is intentionally limited to exactly two endpoints:
    GET /repos/{owner}/{repo}
    GET /repos/{owner}/{repo}/languages

The client is responsible only for making HTTP calls and translating
transport-level/HTTP-status failures into the application's custom
exceptions. It does not know about `RepositoryMetadata` — response
mapping is handled in the service layer.
"""

import logging
from typing import Any, Dict

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitExceededError,
    RepositoryNotFoundError,
)

logger = logging.getLogger(__name__)


class GitHubClient:
    """Async client for read-only access to public GitHub repository data."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._base_url = self._settings.github_api_base_url.rstrip("/")
        self._timeout = self._settings.github_api_timeout_seconds

    def _headers(self) -> Dict[str, str]:
        """Build request headers, including the bearer token from settings."""
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._settings.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _get(self, path: str, owner: str, repo: str) -> Dict[str, Any]:
        """
        Perform a GET request against the GitHub API and raise a mapped
        application exception on failure.

        Args:
            path: API path, e.g. "/repos/{owner}/{repo}".
            owner: Repository owner (used only for error messages).
            repo: Repository name (used only for error messages).
        """
        url = f"{self._base_url}{path}"
        logger.debug("Calling GitHub API: GET %s", url)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers=self._headers())
        except httpx.TimeoutException as exc:
            logger.error("GitHub API request timed out: %s", url)
            raise GitHubAPIError(
                f"Timed out while contacting GitHub API for '{owner}/{repo}'."
            ) from exc
        except httpx.RequestError as exc:
            logger.error("GitHub API network error: %s | %s", url, exc)
            raise GitHubAPIError(
                f"Network error while contacting GitHub API for '{owner}/{repo}'."
            ) from exc

        if response.status_code == 200:
            return response.json()

        if response.status_code == 404:
            logger.info("Repository not found on GitHub: %s/%s", owner, repo)
            raise RepositoryNotFoundError(
                f"Repository '{owner}/{repo}' was not found on GitHub. "
                "It may be private, misspelled, or deleted."
            )

        if response.status_code == 401:
            logger.error("GitHub authentication failed (invalid/missing token).")
            raise GitHubAuthenticationError(
                "GitHub authentication failed. Verify GITHUB_TOKEN in the .env file."
            )

        if response.status_code in (403, 429):
            logger.warning("GitHub API rate limit exceeded for %s/%s.", owner, repo)
            raise GitHubRateLimitExceededError(
                "GitHub API rate limit exceeded. Please try again later."
            )

        logger.error(
            "Unexpected GitHub API response: %s | status=%s | body=%s",
            url,
            response.status_code,
            response.text[:500],
        )
        raise GitHubAPIError(
            f"Unexpected GitHub API error (status {response.status_code}) "
            f"while fetching '{owner}/{repo}'."
        )

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Call GET /repos/{owner}/{repo} and return the raw JSON payload."""
        return await self._get(f"/repos/{owner}/{repo}", owner, repo)

    async def get_repository_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Call GET /repos/{owner}/{repo}/languages and return {language: bytes}."""
        return await self._get(f"/repos/{owner}/{repo}/languages", owner, repo)
