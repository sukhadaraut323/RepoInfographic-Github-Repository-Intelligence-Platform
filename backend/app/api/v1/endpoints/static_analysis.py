"""
API endpoint for Module 3 — Static Code Analysis.

Exposes a single route:
    POST /api/v1/repository/scan

Note: this endpoint is a synchronous (`def`, not `async def`) path
operation, consistent with Module 2's clone endpoint — filesystem
traversal and file reads are blocking I/O, so FastAPI runs this in its
worker threadpool rather than on the event loop.
"""

import logging

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException

from app.core.config import get_settings
from app.core.exceptions import RepositoryPathNotFoundError, StaticAnalysisError
from app.schemas.static_analysis import StaticAnalysisRequest, StaticAnalysisResult
from app.services.file_analyzer import FileAnalyzer
from app.services.language_detector import LanguageDetector
from app.services.repository_scanner import RepositoryScanner
from app.services.static_analysis_service import StaticAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repository", tags=["Static Code Analysis"])


def get_static_analysis_service() -> StaticAnalysisService:
    """
    Dependency provider for StaticAnalysisService.

    Kept as a function (rather than a module-level singleton) so tests can
    override it via FastAPI's `app.dependency_overrides`.
    """
    settings = get_settings()
    scanner = RepositoryScanner(
        ignored_directories=settings.static_analysis_ignored_directories,
        tree_max_depth=settings.static_analysis_tree_max_depth,
        tree_max_entries_per_level=settings.static_analysis_tree_max_entries_per_level,
    )
    file_analyzer = FileAnalyzer(max_file_size_bytes=settings.static_analysis_max_file_size_bytes)
    return StaticAnalysisService(
        scanner=scanner,
        file_analyzer=file_analyzer,
        language_detector=LanguageDetector(),
        ignored_directories=settings.static_analysis_ignored_directories,
    )


@router.post(
    "/scan",
    response_model=StaticAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Run static (non-executing) analysis on a cloned repository",
    description=(
        "Scans a locally cloned repository (as produced by Module 2) and "
        "reports file/directory counts, language distribution, line "
        "statistics, detected project types, and a shallow directory tree. "
        "No repository code is executed, and no complexity, dependency, "
        "security, or AI-derived data is computed."
    ),
)
def scan_repository(
    request: StaticAnalysisRequest,
    service: StaticAnalysisService = Depends(get_static_analysis_service),
) -> StaticAnalysisResult:
    """Run static analysis on the given local repository path."""
    try:
        return service.analyze(request.local_path)
    except RepositoryPathNotFoundError as exc:
        logger.warning("Repository path not found: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except StaticAnalysisError as exc:
        logger.error("Static analysis error: %s", exc.message)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc
