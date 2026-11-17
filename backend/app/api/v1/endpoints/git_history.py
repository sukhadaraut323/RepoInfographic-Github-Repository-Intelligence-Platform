"""
API endpoint for Module 4 — Git History Analysis.

Exposes a single route:
    POST /api/v1/repository/history

Note: this endpoint is a synchronous (`def`, not `async def`) path
operation, consistent with Modules 2 and 3 — GitPython performs blocking
subprocess/filesystem calls, so FastAPI runs this in its worker
threadpool rather than on the event loop.
"""

import logging

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException

from app.core.config import get_settings
from app.core.exceptions import (
    GitHistoryAnalysisError,
    NotAGitRepositoryError,
    RepositoryPathNotFoundError,
)
from app.schemas.git_history import GitHistoryRequest, GitHistoryResult
from app.services.git_history_analyzer import GitHistoryAnalyzer
from app.services.git_history_service import GitHistoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repository", tags=["Git History Analysis"])


def get_git_history_service() -> GitHistoryService:
    """
    Dependency provider for GitHistoryService.

    Kept as a function (rather than a module-level singleton) so tests can
    override it via FastAPI's `app.dependency_overrides`.
    """
    settings = get_settings()
    return GitHistoryService(
        analyzer=GitHistoryAnalyzer(),
        activity_window_days=settings.git_history_activity_window_days,
        high_activity_threshold=settings.git_history_high_activity_threshold,
        medium_activity_threshold=settings.git_history_medium_activity_threshold,
        low_activity_threshold=settings.git_history_low_activity_threshold,
    )


@router.post(
    "/history",
    response_model=GitHistoryResult,
    status_code=status.HTTP_200_OK,
    summary="Analyze the local git commit history of a cloned repository",
    description=(
        "Reads commit and branch metadata directly from a locally cloned "
        "repository's `.git` directory (as produced by Module 2) and "
        "returns structured engineering history: commit counts, "
        "contributor counts, branch counts, commit-frequency averages, a "
        "monthly commit timeline, and a coarse recent-activity level. "
        "The GitHub REST API is never called, and no blame, release, "
        "merge, code-ownership, or AI-derived analysis is performed."
    ),
)
def get_repository_history(
    request: GitHistoryRequest,
    service: GitHistoryService = Depends(get_git_history_service),
) -> GitHistoryResult:
    """Analyze and return the git history of the given local repository."""
    try:
        return service.analyze(request.local_path)
    except RepositoryPathNotFoundError as exc:
        logger.warning("Repository path not found: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except NotAGitRepositoryError as exc:
        logger.warning("Not a git repository: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except GitHistoryAnalysisError as exc:
        logger.error("Git history analysis error: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc
