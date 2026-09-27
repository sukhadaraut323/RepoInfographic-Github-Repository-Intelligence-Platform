"""
API endpoint for Module 1 — GitHub Repository Metadata Collector.

Exposes a single route:
    POST /api/v1/repository/analyze
"""

import logging

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException

from app.clients.github_client import GitHubClient
from app.core.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitExceededError,
    InvalidRepositoryURLError,
    RepositoryNotFoundError,
)
from app.schemas.repository import RepositoryAnalyzeRequest, RepositoryMetadata
from app.services.repository_service import RepositoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repository", tags=["Repository Metadata"])


def get_repository_service() -> RepositoryService:
    """
    Dependency provider for RepositoryService.

    Kept as a function (rather than a module-level singleton) so tests can
    override it via FastAPI's `app.dependency_overrides`.
    """
    return RepositoryService(github_client=GitHubClient())


@router.post(
    "/analyze",
    response_model=RepositoryMetadata,
    status_code=status.HTTP_200_OK,
    summary="Collect GitHub repository metadata and language breakdown",
    description=(
        "Given a public GitHub repository URL, fetches repository metadata "
        "and the language breakdown directly from the GitHub REST API and "
        "returns them as a structured `RepositoryMetadata` object. "
        "No data is persisted and no metrics are computed or inferred."
    ),
)
async def analyze_repository(
    request: RepositoryAnalyzeRequest,
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryMetadata:
    """Collect and return repository metadata for the given GitHub URL."""
    try:
        return await service.analyze_repository(request.repository_url)
    except InvalidRepositoryURLError as exc:
        logger.warning("Invalid repository URL: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except GitHubAuthenticationError as exc:
        logger.error("GitHub authentication error: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc
    except GitHubRateLimitExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message) from exc
    except GitHubAPIError as exc:
        logger.error("GitHub API error: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc
