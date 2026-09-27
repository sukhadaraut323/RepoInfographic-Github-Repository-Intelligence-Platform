"""
API endpoint for Module 2 — Repository Cloner.

Exposes a single route:
    POST /api/v1/repository/clone

Note: this endpoint is a synchronous (`def`, not `async def`) path
operation. GitPython performs blocking subprocess calls to the system
`git` binary, so FastAPI is left to run it in its worker threadpool
rather than blocking the event loop, consistent with FastAPI's own
guidance for wrapping blocking I/O libraries.
"""

import logging

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException

from app.clients.git_client import GitRepositoryClient
from app.core.exceptions import (
    InvalidGitReferenceError,
    InvalidRepositoryURLError,
    RepositoryCloneError,
)
from app.schemas.clone_result import RepositoryCloneRequest, RepositoryCloneResult
from app.services.repository_cloner_service import RepositoryClonerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repository", tags=["Repository Cloner"])


def get_repository_cloner_service() -> RepositoryClonerService:
    """
    Dependency provider for RepositoryClonerService.

    Kept as a function (rather than a module-level singleton) so tests can
    override it via FastAPI's `app.dependency_overrides`.
    """
    return RepositoryClonerService(git_client=GitRepositoryClient())


@router.post(
    "/clone",
    response_model=RepositoryCloneResult,
    status_code=status.HTTP_200_OK,
    summary="Clone or update a local working copy of a public GitHub repository",
    description=(
        "Clones a public GitHub repository into a managed local workspace "
        "directory (`workspace/{owner}_{repo}`). If a local copy already "
        "exists, it is fetched/pulled in place instead of being re-cloned. "
        "No static analysis, git history analysis, or metrics are computed here."
    ),
)
def clone_repository(
    request: RepositoryCloneRequest,
    service: RepositoryClonerService = Depends(get_repository_cloner_service),
) -> RepositoryCloneResult:
    """Clone or update the given repository and return the outcome."""
    try:
        return service.clone_or_update_repository(request.repository_url, request.branch)
    except InvalidRepositoryURLError as exc:
        logger.warning("Invalid repository URL: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except InvalidGitReferenceError as exc:
        logger.warning("Invalid git reference: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except RepositoryCloneError as exc:
        logger.error("Repository clone error: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc
